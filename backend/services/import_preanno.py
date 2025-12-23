"""
预标注导入服务模块
"""
import json
from pathlib import Path
from typing import List, Optional
from loguru import logger

from core.config import DATA_DIR
from api.schemas import PreAnnotationImport, ImageStatus
from services.annotation import annotation_service


class ImportService:
    """预标注导入服务"""
    
    def __init__(self):
        self.preannotations: dict[str, dict[str, PreAnnotationImport]] = {}
    
    def import_file(self, file_path: str, dataset_type: str, 
                    auto_accept_threshold: float = 0.95) -> dict:
        """导入预标注文件
        
        Args:
            file_path: JSONL文件路径
            dataset_type: 数据类型
            auto_accept_threshold: 自动接受阈值（置信度高于此值自动标注）
        
        Returns:
            导入统计
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if dataset_type not in self.preannotations:
            self.preannotations[dataset_type] = {}
        
        imported = 0
        auto_accepted = 0
        errors = 0
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    preanno = PreAnnotationImport(**data)
                    
                    # 存储预标注
                    self.preannotations[dataset_type][preanno.image_path] = preanno
                    imported += 1
                    
                    # 检查是否自动接受
                    if preanno.confidence_score >= auto_accept_threshold:
                        annotation_service.annotate(
                            preanno.image_path,
                            preanno.predicted_label,
                            dataset_type
                        )
                        auto_accepted += 1
                    
                except Exception as e:
                    logger.warning(f"解析预标注失败: {e}")
                    errors += 1
        
        logger.info(f"导入预标注完成: 共{imported}条, 自动接受{auto_accepted}条, 错误{errors}条")
        
        return {
            "imported": imported,
            "auto_accepted": auto_accepted,
            "errors": errors
        }
    
    def get_preannotation(self, dataset_type: str, image_path: str) -> Optional[PreAnnotationImport]:
        """获取预标注"""
        return self.preannotations.get(dataset_type, {}).get(image_path)
    
    def has_preannotation(self, dataset_type: str, image_path: str) -> bool:
        """检查是否有预标注"""
        return image_path in self.preannotations.get(dataset_type, {})


# 全局导入服务实例
import_service = ImportService()
