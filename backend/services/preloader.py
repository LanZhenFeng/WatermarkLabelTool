"""
图片预加载服务模块
"""
import asyncio
import base64
import io
from pathlib import Path
from typing import Dict, Optional, Tuple
from collections import OrderedDict
from loguru import logger
from PIL import Image

from core.config import config_manager
from services.dataset import dataset_service


class PreloadCache:
    """LRU 预加载缓存"""
    
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._cache: OrderedDict[str, bytes] = OrderedDict()
    
    def get(self, key: str) -> Optional[bytes]:
        """获取缓存"""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, key: str, value: bytes):
        """添加缓存"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def __contains__(self, key: str) -> bool:
        return key in self._cache


class PreloadService:
    """预加载服务"""
    
    _instance: Optional["PreloadService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.cache = PreloadCache(max_size=30)
        self._preload_task: Optional[asyncio.Task] = None
        self._current_dataset: Optional[str] = None
        self._current_index: int = 0
        logger.info("预加载服务初始化完成")
    
    def _load_image(self, image_path: str, max_size: int = 1200) -> Optional[bytes]:
        """加载并压缩图片"""
        try:
            path = Path(image_path)
            if not path.exists():
                logger.warning(f"图片不存在: {image_path}")
                return None
            
            # 打开图片
            with Image.open(path) as img:
                # 转换为RGB（处理RGBA等格式）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 缩放图片
                width, height = img.size
                if max(width, height) > max_size:
                    ratio = max_size / max(width, height)
                    new_size = (int(width * ratio), int(height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # 转换为JPEG字节
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"加载图片失败 {image_path}: {e}")
            return None
    
    def get_image(self, image_path: str) -> Optional[Tuple[bytes, str]]:
        """获取图片（优先从缓存）"""
        # 检查缓存
        cached = self.cache.get(image_path)
        if cached:
            logger.debug(f"缓存命中: {image_path}")
            return cached, "image/jpeg"
        
        # 加载图片
        data = self._load_image(image_path)
        if data:
            self.cache.put(image_path, data)
            return data, "image/jpeg"
        
        return None
    
    def get_image_base64(self, image_path: str) -> Optional[str]:
        """获取图片的Base64编码"""
        result = self.get_image(image_path)
        if result:
            data, _ = result
            return base64.b64encode(data).decode('utf-8')
        return None
    
    async def preload_around(self, dataset_type: str, current_index: int):
        """预加载当前索引周围的图片"""
        images = dataset_service.get_images(dataset_type)
        if not images:
            return
        
        window = config_manager.config.settings.preload_window
        half_window = window // 2
        
        # 计算预加载范围
        start = max(0, current_index - half_window)
        end = min(len(images), current_index + half_window + 1)
        
        preload_paths = images[start:end]
        
        # 异步预加载
        for path in preload_paths:
            if path not in self.cache:
                # 使用线程池执行IO操作
                await asyncio.get_event_loop().run_in_executor(
                    None, self._preload_single, path
                )
                await asyncio.sleep(0.01)  # 给其他任务让路
    
    def _preload_single(self, image_path: str):
        """预加载单张图片"""
        if image_path in self.cache:
            return
        
        data = self._load_image(image_path)
        if data:
            self.cache.put(image_path, data)
            logger.debug(f"预加载完成: {Path(image_path).name}")
    
    def start_preload(self, dataset_type: str, current_index: int):
        """启动预加载任务"""
        self._current_dataset = dataset_type
        self._current_index = current_index
        
        # 如果有正在运行的任务，取消它
        if self._preload_task and not self._preload_task.done():
            self._preload_task.cancel()
        
        # 创建新的预加载任务
        try:
            loop = asyncio.get_event_loop()
            self._preload_task = loop.create_task(
                self.preload_around(dataset_type, current_index)
            )
        except RuntimeError:
            # 如果没有事件循环，同步预加载当前图片
            images = dataset_service.get_images(dataset_type)
            if images and 0 <= current_index < len(images):
                self._preload_single(images[current_index])


# 全局预加载服务实例
preload_service = PreloadService()
