"""
数据集服务模块 - 管理数据类型和图片列表
"""
import os
from pathlib import Path
from typing import List, Optional
from loguru import logger

from core.config import config_manager, DatasetType
from api.schemas import ImageStatus, DatasetTypeResponse, ImageInfo
from services.annotation import annotation_service


class DatasetService:
    """数据集服务"""
    
    _instance: Optional["DatasetService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        # 缓存图片列表
        self._image_cache: dict[str, List[str]] = {}
        logger.info("数据集服务初始化完成")
    
    def get_supported_extensions(self) -> set:
        """获取支持的图片扩展名"""
        formats = config_manager.config.settings.supported_formats
        extensions = set()
        for fmt in formats:
            extensions.add(f".{fmt.lower()}")
        return extensions
    
    def scan_images(self, image_dir: str, recursive: bool = True, 
                     exclude_dirs: List[str] = None) -> List[str]:
        """扫描目录中的图片
        
        Args:
            image_dir: 图片目录路径
            recursive: 是否递归扫描子目录
            exclude_dirs: 要排除的子目录名称列表
        """
        path = Path(image_dir)
        if not path.exists():
            logger.warning(f"目录不存在: {image_dir}")
            return []
        
        extensions = self.get_supported_extensions()
        exclude_dirs = set(exclude_dirs or [])
        images = []
        
        def should_exclude(dir_path: Path) -> bool:
            """检查目录是否应被排除"""
            # 检查目录名是否在排除列表中
            for exclude in exclude_dirs:
                if dir_path.name == exclude:
                    return True
                # 支持路径匹配，如 "subdir/nested"
                if exclude in str(dir_path):
                    return True
            return False
        
        def scan_dir(dir_path: Path):
            """扫描单个目录"""
            try:
                for item in sorted(dir_path.iterdir()):
                    if item.is_file() and item.suffix.lower() in extensions:
                        images.append(str(item.absolute()))
                    elif item.is_dir() and recursive and not should_exclude(item):
                        scan_dir(item)
            except PermissionError:
                logger.warning(f"权限不足，跳过目录: {dir_path}")
        
        scan_dir(path)
        
        logger.info(f"扫描到 {len(images)} 张图片: {image_dir} (递归={recursive}, 排除={list(exclude_dirs)})")
        return images
    
    def get_images(self, dataset_type: str, refresh: bool = False) -> List[str]:
        """获取数据类型的图片列表"""
        if not refresh and dataset_type in self._image_cache:
            return self._image_cache[dataset_type]
        
        dt = config_manager.get_dataset_type(dataset_type)
        if dt is None:
            return []
        
        images = self.scan_images(dt.image_dir, dt.recursive, dt.exclude_dirs)
        self._image_cache[dataset_type] = images
        return images
    
    def get_image_info(self, dataset_type: str, index: int) -> Optional[ImageInfo]:
        """获取指定索引的图片信息"""
        images = self.get_images(dataset_type)
        if index < 0 or index >= len(images):
            return None
        
        image_path = images[index]
        status = annotation_service.get_image_status(dataset_type, image_path)
        
        label = None
        if dataset_type in annotation_service.annotations:
            anno = annotation_service.annotations[dataset_type].get(image_path)
            if anno:
                label = anno.label
        
        return ImageInfo(
            path=image_path,
            filename=Path(image_path).name,
            index=index,
            status=status,
            label=label
        )
    
    def get_all_types(self, skip_scan: bool = False) -> List[DatasetTypeResponse]:
        """获取所有数据类型
        
        Args:
            skip_scan: 如果True，跳过图片扫描（使用缓存或显示-1）
        """
        result = []
        for dt in config_manager.config.dataset_types:
            # 优化：跳过扫描时使用缓存值或显示为未知
            if skip_scan and dt.name not in self._image_cache:
                total_images = -1  # 表示尚未扫描
                annotated_count = 0
            else:
                images = self.get_images(dt.name)
                progress = annotation_service.get_progress(dt.name, len(images))
                total_images = len(images)
                annotated_count = progress["annotated_count"]
            
            result.append(DatasetTypeResponse(
                name=dt.name,
                description=dt.description,
                image_dir=dt.image_dir,
                recursive=dt.recursive,
                exclude_dirs=dt.exclude_dirs,
                target_count=dt.target_count.model_dump(),
                current_count=dt.current_count.model_dump(),
                priority=dt.priority,
                total_images=total_images,
                annotated_count=annotated_count
            ))
        
        return sorted(result, key=lambda x: x.priority)
    
    def add_type(self, name: str, description: str, image_dir: str,
                 target_watermarked: int = 0, target_non_watermarked: int = 0,
                 priority: int = 1, recursive: bool = True,
                 exclude_dirs: List[str] = None) -> DatasetTypeResponse:
        """添加数据类型"""
        from core.config import TargetCount, CurrentCount
        
        dt = DatasetType(
            name=name,
            description=description,
            image_dir=image_dir,
            recursive=recursive,
            exclude_dirs=exclude_dirs or [],
            target_count=TargetCount(
                watermarked=target_watermarked,
                non_watermarked=target_non_watermarked
            ),
            current_count=CurrentCount(),
            priority=priority
        )
        
        config_manager.add_dataset_type(dt)
        
        # 刷新缓存
        if name in self._image_cache:
            del self._image_cache[name]
        
        images = self.get_images(name)
        progress = annotation_service.get_progress(name, len(images))
        
        logger.info(f"添加数据类型: {name}")
        
        return DatasetTypeResponse(
            name=dt.name,
            description=dt.description,
            image_dir=dt.image_dir,
            recursive=dt.recursive,
            exclude_dirs=dt.exclude_dirs,
            target_count=dt.target_count.model_dump(),
            current_count=dt.current_count.model_dump(),
            priority=dt.priority,
            total_images=len(images),
            annotated_count=progress["annotated_count"]
        )
    
    def update_type(self, name: str, description: Optional[str] = None,
                    image_dir: Optional[str] = None,
                    target_watermarked: Optional[int] = None,
                    target_non_watermarked: Optional[int] = None,
                    priority: Optional[int] = None) -> Optional[DatasetTypeResponse]:
        """更新数据类型"""
        dt = config_manager.get_dataset_type(name)
        if dt is None:
            return None
        
        if description is not None:
            dt.description = description
        if image_dir is not None:
            dt.image_dir = image_dir
            # 刷新缓存
            if name in self._image_cache:
                del self._image_cache[name]
        if target_watermarked is not None:
            dt.target_count.watermarked = target_watermarked
        if target_non_watermarked is not None:
            dt.target_count.non_watermarked = target_non_watermarked
        if priority is not None:
            dt.priority = priority
        
        config_manager.save()
        
        images = self.get_images(name)
        progress = annotation_service.get_progress(name, len(images))
        
        logger.info(f"更新数据类型: {name}")
        
        return DatasetTypeResponse(
            name=dt.name,
            description=dt.description,
            image_dir=dt.image_dir,
            target_count=dt.target_count.model_dump(),
            current_count=dt.current_count.model_dump(),
            priority=dt.priority,
            total_images=len(images),
            annotated_count=progress["annotated_count"]
        )
    
    def remove_type(self, name: str) -> bool:
        """删除数据类型"""
        result = config_manager.remove_dataset_type(name)
        if result:
            if name in self._image_cache:
                del self._image_cache[name]
            logger.info(f"删除数据类型: {name}")
        return result
    
    def refresh_cache(self, dataset_type: Optional[str] = None):
        """刷新缓存"""
        if dataset_type:
            if dataset_type in self._image_cache:
                del self._image_cache[dataset_type]
            self.get_images(dataset_type, refresh=True)
        else:
            self._image_cache.clear()
            for dt in config_manager.config.dataset_types:
                self.get_images(dt.name, refresh=True)


# 全局数据集服务实例
dataset_service = DatasetService()
