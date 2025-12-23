"""
API 路由定义
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response
from loguru import logger

from api.schemas import (
    DatasetTypeCreate, DatasetTypeResponse, 
    ImageInfo, AnnotationCreate, AnnotationResponse,
    ProgressResponse, ApiResponse, ExportRequest
)
from services.dataset import dataset_service
from services.annotation import annotation_service
from services.preloader import preload_service
from services.export import export_service
from services.import_preanno import import_service


router = APIRouter(prefix="/api")


# ============ 数据类型管理 ============

@router.get("/types", response_model=list[DatasetTypeResponse])
async def get_types():
    """获取所有数据类型"""
    return dataset_service.get_all_types()


@router.post("/types", response_model=DatasetTypeResponse)
async def create_type(data: DatasetTypeCreate):
    """创建数据类型"""
    return dataset_service.add_type(
        name=data.name,
        description=data.description,
        image_dir=data.image_dir,
        target_watermarked=data.target_count.watermarked,
        target_non_watermarked=data.target_count.non_watermarked,
        priority=data.priority,
        recursive=data.recursive,
        exclude_dirs=data.exclude_dirs
    )


@router.put("/types/{name}", response_model=DatasetTypeResponse)
async def update_type(
    name: str,
    description: Optional[str] = None,
    image_dir: Optional[str] = None,
    target_watermarked: Optional[int] = None,
    target_non_watermarked: Optional[int] = None,
    priority: Optional[int] = None
):
    """更新数据类型"""
    result = dataset_service.update_type(
        name=name,
        description=description,
        image_dir=image_dir,
        target_watermarked=target_watermarked,
        target_non_watermarked=target_non_watermarked,
        priority=priority
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"数据类型不存在: {name}")
    return result


@router.delete("/types/{name}")
async def delete_type(name: str):
    """删除数据类型"""
    if dataset_service.remove_type(name):
        return ApiResponse(success=True, message=f"已删除: {name}")
    raise HTTPException(status_code=404, detail=f"数据类型不存在: {name}")


# ============ 图片管理 ============

@router.get("/images")
async def get_images(
    dataset_type: str,
    refresh: bool = False
):
    """获取图片列表"""
    images = dataset_service.get_images(dataset_type, refresh)
    return {
        "dataset_type": dataset_type,
        "total": len(images),
        "images": [
            {
                "path": img,
                "index": i,
                "status": annotation_service.get_image_status(dataset_type, img).value
            }
            for i, img in enumerate(images)
        ]
    }


@router.get("/images/current", response_model=ImageInfo)
async def get_current_image(
    dataset_type: str,
    background_tasks: BackgroundTasks
):
    """获取当前待标注图片"""
    current_index = annotation_service.get_current_index(dataset_type)
    info = dataset_service.get_image_info(dataset_type, current_index)
    
    if info is None:
        raise HTTPException(status_code=404, detail="没有可用的图片")
    
    # 后台启动预加载
    background_tasks.add_task(preload_service.start_preload, dataset_type, current_index)
    
    return info


@router.get("/images/{index}", response_model=ImageInfo)
async def get_image_by_index(
    dataset_type: str,
    index: int,
    background_tasks: BackgroundTasks
):
    """获取指定索引的图片信息"""
    info = dataset_service.get_image_info(dataset_type, index)
    
    if info is None:
        raise HTTPException(status_code=404, detail=f"图片不存在: index={index}")
    
    # 更新当前索引
    annotation_service.set_current_index(dataset_type, index)
    
    # 后台启动预加载
    background_tasks.add_task(preload_service.start_preload, dataset_type, index)
    
    return info


@router.get("/images/data/{index}")
async def get_image_data(
    dataset_type: str,
    index: int
):
    """获取图片数据（Base64编码）"""
    images = dataset_service.get_images(dataset_type)
    if index < 0 or index >= len(images):
        raise HTTPException(status_code=404, detail="图片不存在")
    
    image_path = images[index]
    result = preload_service.get_image(image_path)
    
    if result is None:
        raise HTTPException(status_code=500, detail="图片加载失败")
    
    data, content_type = result
    return Response(content=data, media_type=content_type)


@router.get("/images/base64/{index}")
async def get_image_base64(
    dataset_type: str,
    index: int
):
    """获取图片的Base64编码"""
    images = dataset_service.get_images(dataset_type)
    if index < 0 or index >= len(images):
        raise HTTPException(status_code=404, detail="图片不存在")
    
    image_path = images[index]
    base64_data = preload_service.get_image_base64(image_path)
    
    if base64_data is None:
        raise HTTPException(status_code=500, detail="图片加载失败")
    
    return {"base64": base64_data, "path": image_path}


# ============ 标注管理 ============

@router.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(data: AnnotationCreate):
    """创建标注"""
    return annotation_service.annotate(
        image_path=data.image_path,
        label=data.label,
        dataset_type=data.dataset_type
    )


@router.post("/annotations/skip")
async def skip_image(
    dataset_type: str,
    image_path: str
):
    """跳过图片"""
    annotation_service.skip(image_path, dataset_type)
    return ApiResponse(success=True, message="已跳过")


@router.post("/annotations/undo")
async def undo_annotation():
    """撤销操作"""
    action = annotation_service.undo()
    if action:
        return ApiResponse(
            success=True, 
            message="已撤销",
            data=action.to_dict()
        )
    return ApiResponse(success=False, message="没有可撤销的操作")


@router.post("/annotations/redo")
async def redo_annotation():
    """重做操作"""
    action = annotation_service.redo()
    if action:
        return ApiResponse(
            success=True,
            message="已重做",
            data=action.to_dict()
        )
    return ApiResponse(success=False, message="没有可重做的操作")


# ============ 进度管理 ============

@router.get("/progress", response_model=ProgressResponse)
async def get_progress(dataset_type: str):
    """获取标注进度"""
    images = dataset_service.get_images(dataset_type)
    progress = annotation_service.get_progress(dataset_type, len(images))
    return ProgressResponse(**progress)


@router.post("/progress/save")
async def save_progress():
    """保存进度"""
    annotation_service.save_annotations()
    annotation_service.save_session_state()
    return ApiResponse(success=True, message="进度已保存")


@router.get("/progress/session")
async def get_session_stats():
    """获取会话统计"""
    return annotation_service.get_session_stats()


# ============ 导入导出 ============

@router.post("/export")
async def export_annotations(data: ExportRequest):
    """导出标注结果"""
    output_path = export_service.export_jsonl(data.dataset_type, data.output_path)
    return ApiResponse(
        success=True,
        message=f"导出成功",
        data={"output_path": output_path}
    )


@router.get("/export/statistics")
async def get_statistics():
    """获取统计信息"""
    return export_service.export_statistics()


@router.post("/import/preannotation")
async def import_preannotation(
    file_path: str,
    dataset_type: str,
    auto_accept_threshold: float = 0.95
):
    """导入预标注文件"""
    try:
        result = import_service.import_file(file_path, dataset_type, auto_accept_threshold)
        return ApiResponse(success=True, message="导入成功", data=result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 导航 ============

@router.post("/navigate/next")
async def navigate_next(
    dataset_type: str,
    background_tasks: BackgroundTasks
):
    """导航到下一张"""
    images = dataset_service.get_images(dataset_type)
    current = annotation_service.get_current_index(dataset_type)
    
    if current < len(images) - 1:
        new_index = current + 1
        annotation_service.set_current_index(dataset_type, new_index)
        background_tasks.add_task(preload_service.start_preload, dataset_type, new_index)
        return dataset_service.get_image_info(dataset_type, new_index)
    
    return ApiResponse(success=False, message="已经是最后一张")


@router.post("/navigate/prev")
async def navigate_prev(
    dataset_type: str,
    background_tasks: BackgroundTasks
):
    """导航到上一张"""
    current = annotation_service.get_current_index(dataset_type)
    
    if current > 0:
        new_index = current - 1
        annotation_service.set_current_index(dataset_type, new_index)
        background_tasks.add_task(preload_service.start_preload, dataset_type, new_index)
        return dataset_service.get_image_info(dataset_type, new_index)
    
    return ApiResponse(success=False, message="已经是第一张")


@router.post("/navigate/goto")
async def navigate_goto(
    dataset_type: str,
    index: int,
    background_tasks: BackgroundTasks
):
    """跳转到指定索引"""
    images = dataset_service.get_images(dataset_type)
    
    if 0 <= index < len(images):
        annotation_service.set_current_index(dataset_type, index)
        background_tasks.add_task(preload_service.start_preload, dataset_type, index)
        return dataset_service.get_image_info(dataset_type, index)
    
    raise HTTPException(status_code=400, detail="索引超出范围")
