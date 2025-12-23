"""
配置管理模块
"""
import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class TargetCount(BaseModel):
    """目标样本数"""
    watermarked: int = 0
    non_watermarked: int = 0


class CurrentCount(BaseModel):
    """当前已标注数"""
    watermarked: int = 0
    non_watermarked: int = 0


class DatasetType(BaseModel):
    """数据类型配置"""
    name: str
    description: str = ""
    image_dir: str
    recursive: bool = True  # 是否递归扫描子目录
    exclude_dirs: List[str] = Field(default_factory=list)  # 排除的子目录名称
    target_count: TargetCount = Field(default_factory=TargetCount)
    current_count: CurrentCount = Field(default_factory=CurrentCount)
    priority: int = 1


class Settings(BaseModel):
    """全局设置"""
    preload_window: int = 10
    auto_save_interval: int = 10
    supported_formats: List[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "webp", "bmp", "gif", "tiff"]
    )


class Config(BaseModel):
    """完整配置"""
    dataset_types: List[DatasetType] = Field(default_factory=list)
    settings: Settings = Field(default_factory=Settings)


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# 确保目录存在
CONFIG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
(DATA_DIR / "annotations").mkdir(exist_ok=True)
(DATA_DIR / "progress").mkdir(exist_ok=True)
(DATA_DIR / "preannotations").mkdir(exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "dataset_types.yaml"


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional["ConfigManager"] = None
    _config: Optional[Config] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load()
    
    def load(self) -> Config:
        """加载配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # 处理 dataset_types
                dataset_types = []
                for dt in data.get("dataset_types", []):
                    dataset_types.append(DatasetType(**dt))
                
                # 处理 settings
                settings_data = data.get("settings", {})
                settings = Settings(**settings_data)
                
                self._config = Config(
                    dataset_types=dataset_types,
                    settings=settings
                )
        else:
            self._config = Config()
            self.save()
        return self._config
    
    def save(self) -> None:
        """保存配置"""
        if self._config is None:
            return
        
        data = {
            "dataset_types": [dt.model_dump() for dt in self._config.dataset_types],
            "settings": self._config.settings.model_dump()
        }
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    @property
    def config(self) -> Config:
        """获取配置"""
        if self._config is None:
            self.load()
        return self._config
    
    def add_dataset_type(self, dataset_type: DatasetType) -> None:
        """添加数据类型"""
        # 检查是否已存在
        for i, dt in enumerate(self._config.dataset_types):
            if dt.name == dataset_type.name:
                # 更新现有类型
                self._config.dataset_types[i] = dataset_type
                self.save()
                return
        
        self._config.dataset_types.append(dataset_type)
        self.save()
    
    def remove_dataset_type(self, name: str) -> bool:
        """删除数据类型"""
        for i, dt in enumerate(self._config.dataset_types):
            if dt.name == name:
                self._config.dataset_types.pop(i)
                self.save()
                return True
        return False
    
    def get_dataset_type(self, name: str) -> Optional[DatasetType]:
        """获取数据类型"""
        for dt in self._config.dataset_types:
            if dt.name == name:
                return dt
        return None
    
    def update_current_count(self, name: str, label: int) -> None:
        """更新当前已标注数
        
        Args:
            name: 数据类型名称
            label: 标签 (1=有水印, 0=无水印)
        """
        dt = self.get_dataset_type(name)
        if dt:
            if label == 1:
                dt.current_count.watermarked += 1
            else:
                dt.current_count.non_watermarked += 1
            self.save()


# 全局配置管理器实例
config_manager = ConfigManager()
