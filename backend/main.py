"""
水印标注平台 - FastAPI 主入口
"""
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from core.logger import print_welcome, print_status, console
from core.config import PROJECT_ROOT
from api.routes import router
from services.annotation import annotation_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print_welcome()
    print_status("服务启动中...", "info")
    logger.info("水印标注平台启动")
    
    yield
    
    # 关闭时
    print_status("正在保存数据...", "info")
    annotation_service.save_annotations()
    annotation_service.save_session_state()
    print_status("服务已关闭", "success")
    logger.info("水印标注平台关闭")


# 创建应用
app = FastAPI(
    title="水印标注平台",
    description="用于水印检测数据集标注的快速标注工具",
    version="1.0.0",
    lifespan=lifespan
)

# 注册API路由
app.include_router(router)

# 静态文件
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def index():
    """主页"""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "水印标注平台 API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    console.print("\n[bold cyan]🚀 启动服务: http://localhost:8000[/bold cyan]\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
