"""
API Pydantic 数据模型
"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ImageStatus(str, Enum):
    """图片标注状态"""
    PENDING = "pending"           # 待标注
    WATERMARKED = "watermarked"   # 有水印
    NO_WATERMARK = "no_watermark" # 无水印
    SKIPPED = "skipped"           # 已跳过


class TargetCountSchema(BaseModel):
    """目标样本数"""
    watermarked: int = 0
    non_watermarked: int = 0


class CurrentCountSchema(BaseModel):
    """当前已标注数"""
    watermarked: int = 0
    non_watermarked: int = 0


class DatasetTypeCreate(BaseModel):
    """创建数据类型请求"""
    name: str
    description: str = ""
    image_dirs: List[str] = Field(default_factory=list)  # 支持多个图片目录
    recursive: bool = True  # 是否递归扫描子目录
    exclude_dirs: List[str] = Field(default_factory=list)  # 排除的子目录
    target_count: TargetCountSchema = Field(default_factory=TargetCountSchema)
    priority: int = 1


class DatasetTypeResponse(BaseModel):
    """数据类型响应"""
    model_config = {"from_attributes": True}
    
    name: str
    description: str
    image_dirs: List[str] = Field(default_factory=list)  # 支持多个图片目录
    recursive: bool = True
    exclude_dirs: List[str] = Field(default_factory=list)
    target_count: TargetCountSchema
    current_count: CurrentCountSchema
    priority: int
    total_images: int = 0
    annotated_count: int = 0


class ImageInfo(BaseModel):
    """图片信息"""
    path: str
    filename: str
    index: int
    status: ImageStatus = ImageStatus.PENDING
    label: Optional[int] = None  # 0=无水印, 1=有水印


class AnnotationCreate(BaseModel):
    """创建标注请求"""
    image_path: str
    label: int  # 0=无水印, 1=有水印
    dataset_type: str


class AnnotationResponse(BaseModel):
    """标注响应"""
    image_path: str
    label: int
    dataset_type: str
    timestamp: datetime


class ProgressResponse(BaseModel):
    """进度响应"""
    dataset_type: str
    current_index: int
    total_images: int
    annotated_count: int
    skipped_count: int
    watermarked_count: int
    non_watermarked_count: int


class SessionState(BaseModel):
    """会话状态"""
    current_dataset_type: Optional[str] = None
    current_index: int = 0
    history: List[dict] = Field(default_factory=list)
    redo_stack: List[dict] = Field(default_factory=list)


class PreAnnotationImport(BaseModel):
    """预标注导入"""
    image_path: str
    predicted_label: int
    confidence_score: float = 0.0
    source: str = "unknown"


class ExportRequest(BaseModel):
    """导出请求"""
    dataset_type: Optional[str] = None  # 不指定则导出全部
    output_path: Optional[str] = None  # 不指定则使用默认路径


class ApiResponse(BaseModel):
    """通用API响应"""
    success: bool = True
    message: str = ""
    data: Optional[dict] = None
