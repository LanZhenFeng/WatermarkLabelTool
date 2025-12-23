"""
日志系统模块 - 使用 Loguru 和 Rich 实现
"""
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.live import Live
from rich.layout import Layout

from core.config import LOG_DIR


# Rich 控制台
console = Console()


def setup_logger():
    """设置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 添加文件日志
    log_file = LOG_DIR / f"annotation_{datetime.now().strftime('%Y%m%d')}.log"
    logger.add(
        log_file,
        rotation="00:00",  # 每天轮转
        retention="30 days",  # 保留30天
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )
    
    # 添加控制台日志（简化输出）
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>"
    )
    
    return logger


def print_welcome():
    """打印欢迎信息"""
    welcome_text = """
🏷️  水印标注平台 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
快捷键: 1/W=有水印  2/N=无水印  S=跳过
        A/←=上一张  D/→=下一张
        Ctrl+Z=撤销  Ctrl+Y=重做
    """
    console.print(Panel(welcome_text, title="[bold blue]Watermark Label Tool[/bold blue]", border_style="blue"))


def print_progress(dataset_type: str, current: int, total: int, 
                   watermarked: int, non_watermarked: int,
                   session_count: int, session_time: str):
    """打印进度信息"""
    # 创建进度表格
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="cyan")
    table.add_column(style="white")
    
    # 计算百分比
    percent = (current / total * 100) if total > 0 else 0
    bar_length = 20
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    
    table.add_row("📊 当前进度:", f"{dataset_type} [{bar}] {current}/{total} ({percent:.1f}%)")
    table.add_row("🏷️  有水印:", f"{watermarked} 张")
    table.add_row("📄 无水印:", f"{non_watermarked} 张")
    table.add_row("⏱️  本次会话:", f"已标注 {session_count} 张, 用时 {session_time}")
    
    console.print(Panel(table, title="[bold green]标注进度[/bold green]", border_style="green"))


def print_status(message: str, style: str = "info"):
    """打印状态消息"""
    styles = {
        "info": "[blue]ℹ️[/blue]",
        "success": "[green]✅[/green]",
        "warning": "[yellow]⚠️[/yellow]",
        "error": "[red]❌[/red]"
    }
    icon = styles.get(style, styles["info"])
    console.print(f"{icon} {message}")


# 初始化日志
setup_logger()
