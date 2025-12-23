"""
导出服务模块
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

from core.config import DATA_DIR
from services.annotation import annotation_service


class ExportService:
    """导出服务"""
    
    def export_jsonl(self, dataset_type: Optional[str] = None,
                     output_path: Optional[str] = None) -> str:
        """导出标注结果为JSONL格式
        
        Args:
            dataset_type: 数据类型（不指定则导出全部）
            output_path: 输出路径（不指定则使用默认路径）
        
        Returns:
            输出文件路径
        """
        if output_path:
            out_file = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if dataset_type:
                filename = f"annotations_{dataset_type}_{timestamp}.jsonl"
            else:
                filename = f"annotations_all_{timestamp}.jsonl"
            out_file = DATA_DIR / "annotations" / filename
        
        # 确保目录存在
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        count = 0
        with open(out_file, "w", encoding="utf-8") as f:
            if dataset_type:
                # 导出指定类型
                annotations = annotation_service.annotations.get(dataset_type, {})
                for anno in annotations.values():
                    f.write(anno.to_jsonl_line() + "\n")
                    count += 1
            else:
                # 导出全部
                for dt, annotations in annotation_service.annotations.items():
                    for anno in annotations.values():
                        f.write(anno.to_jsonl_line() + "\n")
                        count += 1
        
        logger.info(f"导出完成: {count}条标注 -> {out_file}")
        return str(out_file)
    
    def export_statistics(self) -> dict:
        """导出统计信息"""
        stats = {}
        
        for dt, annotations in annotation_service.annotations.items():
            watermarked = sum(1 for a in annotations.values() if a.label == 1)
            non_watermarked = sum(1 for a in annotations.values() if a.label == 0)
            
            stats[dt] = {
                "total": len(annotations),
                "watermarked": watermarked,
                "non_watermarked": non_watermarked
            }
        
        return stats


# 全局导出服务实例
export_service = ExportService()
