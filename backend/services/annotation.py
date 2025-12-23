"""
标注服务模块 - 管理标注状态和操作
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from loguru import logger

from core.config import DATA_DIR, config_manager
from api.schemas import ImageStatus, AnnotationResponse


class AnnotationAction:
    """标注操作记录"""
    def __init__(self, image_path: str, old_status: ImageStatus, 
                 new_status: ImageStatus, old_label: Optional[int], 
                 new_label: Optional[int], dataset_type: str):
        self.image_path = image_path
        self.old_status = old_status
        self.new_status = new_status
        self.old_label = old_label
        self.new_label = new_label
        self.dataset_type = dataset_type
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "old_status": self.old_status.value,
            "new_status": self.new_status.value,
            "old_label": self.old_label,
            "new_label": self.new_label,
            "dataset_type": self.dataset_type,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnnotationAction":
        action = cls(
            image_path=data["image_path"],
            old_status=ImageStatus(data["old_status"]),
            new_status=ImageStatus(data["new_status"]),
            old_label=data["old_label"],
            new_label=data["new_label"],
            dataset_type=data["dataset_type"]
        )
        action.timestamp = datetime.fromisoformat(data["timestamp"])
        return action


class Annotation:
    """单个标注记录"""
    def __init__(self, image_path: str, label: int, dataset_type: str):
        self.image_path = image_path
        self.label = label  # 0=无水印, 1=有水印
        self.dataset_type = dataset_type
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "label": self.label,
            "dataset_type": self.dataset_type,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_jsonl_line(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AnnotationService:
    """标注服务"""
    
    _instance: Optional["AnnotationService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        # 每个数据类型的标注结果
        self.annotations: Dict[str, Dict[str, Annotation]] = {}  # {dataset_type: {image_path: Annotation}}
        # 每个数据类型的图片状态
        self.image_status: Dict[str, Dict[str, ImageStatus]] = {}  # {dataset_type: {image_path: status}}
        # 已跳过的图片
        self.skipped: Dict[str, Set[str]] = {}  # {dataset_type: set(image_paths)}
        # 当前索引
        self.current_indices: Dict[str, int] = {}  # {dataset_type: index}
        # 操作历史（用于撤销）
        self.history: List[AnnotationAction] = []
        # 重做栈
        self.redo_stack: List[AnnotationAction] = []
        # 本次会话统计
        self.session_start = datetime.now()
        self.session_count = 0
        # 自动保存计数
        self._save_counter = 0
        
        # 加载已有的标注
        self._load_annotations()
        self._load_session_state()
        
        logger.info("标注服务初始化完成")
    
    def _load_annotations(self):
        """加载已有的标注结果"""
        annotations_file = DATA_DIR / "annotations" / "annotations.jsonl"
        if annotations_file.exists():
            with open(annotations_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        dataset_type = data["dataset_type"]
                        image_path = data["image_path"]
                        label = data["label"]
                        
                        if dataset_type not in self.annotations:
                            self.annotations[dataset_type] = {}
                            self.image_status[dataset_type] = {}
                        
                        anno = Annotation(image_path, label, dataset_type)
                        anno.timestamp = datetime.fromisoformat(data["timestamp"])
                        self.annotations[dataset_type][image_path] = anno
                        
                        # 更新状态
                        status = ImageStatus.WATERMARKED if label == 1 else ImageStatus.NO_WATERMARK
                        self.image_status[dataset_type][image_path] = status
                        
                    except Exception as e:
                        logger.warning(f"解析标注记录失败: {e}")
            
            logger.info(f"加载了 {sum(len(a) for a in self.annotations.values())} 条标注记录")
    
    def _load_session_state(self):
        """加载会话状态"""
        state_file = DATA_DIR / "progress" / "session_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.loads(f.read())
                
                # 恢复当前索引
                self.current_indices = data.get("current_indices", {})
                
                # 恢复跳过列表
                skipped_data = data.get("skipped", {})
                for dt, paths in skipped_data.items():
                    self.skipped[dt] = set(paths)
                    # 更新状态
                    if dt not in self.image_status:
                        self.image_status[dt] = {}
                    for path in paths:
                        if path not in self.image_status[dt]:
                            self.image_status[dt][path] = ImageStatus.SKIPPED
                
                logger.info("会话状态恢复成功")
            except Exception as e:
                logger.warning(f"加载会话状态失败: {e}")
    
    def save_session_state(self):
        """保存会话状态"""
        state_file = DATA_DIR / "progress" / "session_state.json"
        data = {
            "current_indices": self.current_indices,
            "skipped": {dt: list(paths) for dt, paths in self.skipped.items()},
            "last_save": datetime.now().isoformat()
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug("会话状态已保存")
    
    def save_annotations(self):
        """保存所有标注到JSONL文件"""
        annotations_file = DATA_DIR / "annotations" / "annotations.jsonl"
        with open(annotations_file, "w", encoding="utf-8") as f:
            for dataset_type, annotations in self.annotations.items():
                for anno in annotations.values():
                    f.write(anno.to_jsonl_line() + "\n")
        logger.info(f"标注结果已保存到 {annotations_file}")
    
    def get_image_status(self, dataset_type: str, image_path: str) -> ImageStatus:
        """获取图片状态"""
        if dataset_type not in self.image_status:
            return ImageStatus.PENDING
        return self.image_status[dataset_type].get(image_path, ImageStatus.PENDING)
    
    def get_current_index(self, dataset_type: str) -> int:
        """获取当前索引"""
        return self.current_indices.get(dataset_type, 0)
    
    def set_current_index(self, dataset_type: str, index: int):
        """设置当前索引"""
        self.current_indices[dataset_type] = index
    
    def annotate(self, image_path: str, label: int, dataset_type: str) -> AnnotationResponse:
        """添加标注"""
        # 初始化数据结构
        if dataset_type not in self.annotations:
            self.annotations[dataset_type] = {}
            self.image_status[dataset_type] = {}
        
        # 记录旧状态
        old_status = self.get_image_status(dataset_type, image_path)
        old_label = None
        if image_path in self.annotations.get(dataset_type, {}):
            old_label = self.annotations[dataset_type][image_path].label
        
        # 创建新标注
        new_status = ImageStatus.WATERMARKED if label == 1 else ImageStatus.NO_WATERMARK
        anno = Annotation(image_path, label, dataset_type)
        
        # 保存标注
        self.annotations[dataset_type][image_path] = anno
        self.image_status[dataset_type][image_path] = new_status
        
        # 从跳过列表移除（如果存在）
        if dataset_type in self.skipped and image_path in self.skipped[dataset_type]:
            self.skipped[dataset_type].discard(image_path)
        
        # 记录操作历史
        action = AnnotationAction(image_path, old_status, new_status, old_label, label, dataset_type)
        self.history.append(action)
        # 清空重做栈
        self.redo_stack.clear()
        
        # 更新统计
        self.session_count += 1
        config_manager.update_current_count(dataset_type, label)
        
        # 自动保存检查
        self._save_counter += 1
        if self._save_counter >= config_manager.config.settings.auto_save_interval:
            self.save_annotations()
            self.save_session_state()
            self._save_counter = 0
        
        logger.info(f"标注完成: {image_path} -> {'有水印' if label == 1 else '无水印'}")
        
        return AnnotationResponse(
            image_path=image_path,
            label=label,
            dataset_type=dataset_type,
            timestamp=anno.timestamp
        )
    
    def skip(self, image_path: str, dataset_type: str):
        """跳过图片"""
        if dataset_type not in self.skipped:
            self.skipped[dataset_type] = set()
        if dataset_type not in self.image_status:
            self.image_status[dataset_type] = {}
        
        old_status = self.get_image_status(dataset_type, image_path)
        old_label = None
        if image_path in self.annotations.get(dataset_type, {}):
            old_label = self.annotations[dataset_type][image_path].label
        
        self.skipped[dataset_type].add(image_path)
        self.image_status[dataset_type][image_path] = ImageStatus.SKIPPED
        
        # 记录操作
        action = AnnotationAction(image_path, old_status, ImageStatus.SKIPPED, old_label, None, dataset_type)
        self.history.append(action)
        self.redo_stack.clear()
        
        logger.info(f"跳过图片: {image_path}")
    
    def undo(self) -> Optional[AnnotationAction]:
        """撤销上一步操作"""
        if not self.history:
            return None
        
        action = self.history.pop()
        self.redo_stack.append(action)
        
        dataset_type = action.dataset_type
        image_path = action.image_path
        
        # 恢复旧状态
        if dataset_type not in self.image_status:
            self.image_status[dataset_type] = {}
        self.image_status[dataset_type][image_path] = action.old_status
        
        # 恢复标注
        if action.old_label is not None:
            if dataset_type not in self.annotations:
                self.annotations[dataset_type] = {}
            anno = Annotation(image_path, action.old_label, dataset_type)
            self.annotations[dataset_type][image_path] = anno
        else:
            # 删除标注
            if dataset_type in self.annotations and image_path in self.annotations[dataset_type]:
                del self.annotations[dataset_type][image_path]
        
        # 恢复跳过状态
        if action.old_status == ImageStatus.SKIPPED:
            if dataset_type not in self.skipped:
                self.skipped[dataset_type] = set()
            self.skipped[dataset_type].add(image_path)
        elif action.new_status == ImageStatus.SKIPPED:
            if dataset_type in self.skipped:
                self.skipped[dataset_type].discard(image_path)
        
        logger.info(f"撤销操作: {image_path}")
        return action
    
    def redo(self) -> Optional[AnnotationAction]:
        """重做操作"""
        if not self.redo_stack:
            return None
        
        action = self.redo_stack.pop()
        self.history.append(action)
        
        dataset_type = action.dataset_type
        image_path = action.image_path
        
        # 应用新状态
        if dataset_type not in self.image_status:
            self.image_status[dataset_type] = {}
        self.image_status[dataset_type][image_path] = action.new_status
        
        # 应用标注
        if action.new_label is not None:
            if dataset_type not in self.annotations:
                self.annotations[dataset_type] = {}
            anno = Annotation(image_path, action.new_label, dataset_type)
            self.annotations[dataset_type][image_path] = anno
        else:
            # 删除标注
            if dataset_type in self.annotations and image_path in self.annotations[dataset_type]:
                del self.annotations[dataset_type][image_path]
        
        # 更新跳过状态
        if action.new_status == ImageStatus.SKIPPED:
            if dataset_type not in self.skipped:
                self.skipped[dataset_type] = set()
            self.skipped[dataset_type].add(image_path)
        
        logger.info(f"重做操作: {image_path}")
        return action
    
    def get_progress(self, dataset_type: str, total_images: int) -> dict:
        """获取进度统计"""
        annotated = len(self.annotations.get(dataset_type, {}))
        skipped = len(self.skipped.get(dataset_type, set()))
        
        watermarked = 0
        non_watermarked = 0
        for anno in self.annotations.get(dataset_type, {}).values():
            if anno.label == 1:
                watermarked += 1
            else:
                non_watermarked += 1
        
        return {
            "dataset_type": dataset_type,
            "current_index": self.get_current_index(dataset_type),
            "total_images": total_images,
            "annotated_count": annotated,
            "skipped_count": skipped,
            "watermarked_count": watermarked,
            "non_watermarked_count": non_watermarked
        }
    
    def get_session_stats(self) -> dict:
        """获取会话统计"""
        elapsed = datetime.now() - self.session_start
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            "session_count": self.session_count,
            "session_time": f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        }


# 全局标注服务实例
annotation_service = AnnotationService()
