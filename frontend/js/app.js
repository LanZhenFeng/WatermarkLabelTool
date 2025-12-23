/**
 * 主应用逻辑
 */

// 应用状态
const state = {
    currentType: null,
    currentIndex: 0,
    currentImage: null,
    types: [],
    isLoading: false,
};

// ============ 初始化 ============

async function init() {
    console.log('🚀 水印标注平台启动');

    // 绑定事件
    document.getElementById('dataset-type').addEventListener('change', (e) => {
        if (e.target.value) {
            selectType(e.target.value);
        }
    });

    // 快速加载数据类型列表（跳过图片扫描）
    await loadTypes(true);

    ui.showToast('欢迎使用水印标注平台', 'info');
}

// ============ 数据类型 ============

async function loadTypes(skipScan = false) {
    try {
        state.types = await api.getTypes(skipScan);
        ui.renderTypeList(state.types, state.currentType);
        ui.renderTypeSelector(state.types, state.currentType);
    } catch (error) {
        ui.showToast('加载数据类型失败: ' + error.message, 'error');
    }
}

async function selectType(typeName) {
    if (state.currentType === typeName) return;

    state.currentType = typeName;
    state.currentIndex = 0;

    ui.renderTypeList(state.types, typeName);
    ui.renderTypeSelector(state.types, typeName);

    // 更新目标统计显示
    updateTargetStats(typeName);

    await loadCurrentImage();
}

// 更新目标进度统计面板
function updateTargetStats(typeName) {
    const type = state.types.find(t => t.name === typeName);
    const statsPanel = document.getElementById('target-stats');

    if (!type) {
        statsPanel.style.display = 'none';
        return;
    }

    const target = type.target_count || {};
    const current = type.current_count || {};
    const hasTarget = (target.watermarked || 0) + (target.non_watermarked || 0) > 0;

    if (!hasTarget) {
        statsPanel.style.display = 'none';
        return;
    }

    statsPanel.style.display = 'flex';

    // 更新有水印统计
    const wmCurrent = current.watermarked || 0;
    const wmTarget = target.watermarked || 0;
    const wmComplete = wmTarget > 0 && wmCurrent >= wmTarget;
    const wmEl = document.getElementById('stat-watermarked');
    wmEl.textContent = `${wmCurrent}/${wmTarget}`;
    wmEl.className = `stat-value ${wmComplete ? 'complete' : ''}`;

    // 更新无水印统计
    const nwmCurrent = current.non_watermarked || 0;
    const nwmTarget = target.non_watermarked || 0;
    const nwmComplete = nwmTarget > 0 && nwmCurrent >= nwmTarget;
    const nwmEl = document.getElementById('stat-no-watermark');
    nwmEl.textContent = `${nwmCurrent}/${nwmTarget}`;
    nwmEl.className = `stat-value ${nwmComplete ? 'complete' : ''}`;
}

async function saveType() {
    const name = document.getElementById('type-name').value.trim();
    const imageDir = document.getElementById('type-dir').value.trim();
    const description = document.getElementById('type-desc').value.trim();
    const recursive = document.getElementById('type-recursive').checked;
    const excludeText = document.getElementById('type-exclude').value.trim();
    const excludeDirs = excludeText ? excludeText.split('\n').map(s => s.trim()).filter(s => s) : [];
    const targetWatermarked = parseInt(document.getElementById('target-watermarked').value) || 0;
    const targetNoWatermark = parseInt(document.getElementById('target-no-watermark').value) || 0;
    const priority = parseInt(document.getElementById('type-priority').value) || 1;

    if (!name || !imageDir) {
        ui.showToast('请填写类型名称和图片目录', 'warning');
        return;
    }

    try {
        await api.createType({
            name,
            description,
            image_dir: imageDir,
            recursive,
            exclude_dirs: excludeDirs,
            target_count: {
                watermarked: targetWatermarked,
                non_watermarked: targetNoWatermark,
            },
            priority,
        });

        ui.showToast('保存成功', 'success');
        closeModal();
        await loadTypes();

        // 自动选择新类型
        selectType(name);
    } catch (error) {
        ui.showToast('保存失败: ' + error.message, 'error');
    }
}

async function editType(name) {
    const type = state.types.find(t => t.name === name);
    if (!type) return;

    document.getElementById('modal-title').textContent = '编辑数据类型';
    document.getElementById('type-name').value = type.name;
    document.getElementById('type-name').disabled = true;
    document.getElementById('type-dir').value = type.image_dir;
    document.getElementById('type-recursive').checked = type.recursive !== false;
    document.getElementById('type-exclude').value = (type.exclude_dirs || []).join('\n');
    document.getElementById('type-desc').value = type.description;
    document.getElementById('target-watermarked').value = type.target_count.watermarked;
    document.getElementById('target-no-watermark').value = type.target_count.non_watermarked;
    document.getElementById('type-priority').value = type.priority;

    document.getElementById('type-modal').classList.add('active');
    closeManageModal();
}

async function deleteType(name) {
    if (!confirm(`确定要删除类型 "${name}" 吗？`)) return;

    try {
        await api.deleteType(name);
        ui.showToast('删除成功', 'success');

        if (state.currentType === name) {
            state.currentType = null;
            ui.hideImage();
            ui.updateFilePath(null);
        }

        await loadTypes();
        refreshManageList();
    } catch (error) {
        ui.showToast('删除失败: ' + error.message, 'error');
    }
}

// ============ 图片加载 ============

async function loadCurrentImage() {
    if (!state.currentType) {
        ui.hideImage();
        return;
    }

    if (state.isLoading) return;
    state.isLoading = true;

    ui.showLoading();

    try {
        // 获取当前图片信息
        const imageInfo = await api.getCurrentImage(state.currentType);
        state.currentImage = imageInfo;
        state.currentIndex = imageInfo.index;

        // 获取进度
        const progress = await api.getProgress(state.currentType);
        ui.updateProgress(progress.annotated_count, progress.total_images);

        // 获取图片数据
        const imageData = await api.getImageBase64(state.currentType, imageInfo.index);
        ui.showImage(imageData.base64);

        // 更新UI
        ui.updateStatusBadge(imageInfo.status);
        ui.updateFilePath(imageInfo.path);

        document.getElementById('current-index').textContent = imageInfo.index + 1;
        document.getElementById('total-images').textContent = progress.total_images;

    } catch (error) {
        ui.showToast('加载图片失败: ' + error.message, 'error');
        ui.hideImage();
    } finally {
        state.isLoading = false;
    }
}

async function loadImageByIndex(index) {
    if (!state.currentType || state.isLoading) return;

    state.isLoading = true;
    ui.showLoading();

    try {
        const imageInfo = await api.getImageByIndex(state.currentType, index);
        state.currentImage = imageInfo;
        state.currentIndex = imageInfo.index;

        const imageData = await api.getImageBase64(state.currentType, index);
        ui.showImage(imageData.base64);

        ui.updateStatusBadge(imageInfo.status);
        ui.updateFilePath(imageInfo.path);

        const progress = await api.getProgress(state.currentType);
        ui.updateProgress(progress.annotated_count, progress.total_images);

        document.getElementById('current-index').textContent = index + 1;

    } catch (error) {
        ui.showToast('加载失败: ' + error.message, 'error');
    } finally {
        state.isLoading = false;
    }
}

// ============ 标注操作 ============

async function annotate(label) {
    if (!state.currentType || !state.currentImage) {
        ui.showToast('请先选择数据类型和图片', 'warning');
        return;
    }

    try {
        await api.createAnnotation(
            state.currentImage.path,
            label,
            state.currentType
        );

        ui.showToast(label === 1 ? '已标记为有水印' : '已标记为无水印', 'success');
        ui.updateStatusBadge(label === 1 ? 'watermarked' : 'no_watermark');

        // 自动跳转到下一张
        await navigateNext();

        // 刷新类型列表显示最新进度
        await loadTypes();

    } catch (error) {
        ui.showToast('标注失败: ' + error.message, 'error');
    }
}

async function skipImage() {
    if (!state.currentType || !state.currentImage) {
        ui.showToast('请先选择数据类型和图片', 'warning');
        return;
    }

    try {
        await api.skipImage(state.currentImage.path, state.currentType);
        ui.showToast('已跳过', 'info');
        ui.updateStatusBadge('skipped');

        await navigateNext();

    } catch (error) {
        ui.showToast('操作失败: ' + error.message, 'error');
    }
}

// ============ 导航 ============

async function navigateNext() {
    if (!state.currentType) return;

    try {
        const result = await api.navigateNext(state.currentType);
        if (result.success === false) {
            ui.showToast('已经是最后一张', 'info');
            return;
        }
        await loadImageByIndex(result.index);
    } catch (error) {
        ui.showToast('导航失败: ' + error.message, 'error');
    }
}

async function navigatePrev() {
    if (!state.currentType) return;

    try {
        const result = await api.navigatePrev(state.currentType);
        if (result.success === false) {
            ui.showToast('已经是第一张', 'info');
            return;
        }
        await loadImageByIndex(result.index);
    } catch (error) {
        ui.showToast('导航失败: ' + error.message, 'error');
    }
}

// ============ 撤销/重做 ============

async function undoAction() {
    try {
        const result = await api.undo();
        if (result.success) {
            ui.showToast('已撤销', 'info');
            await loadCurrentImage();
            await loadTypes();
        } else {
            ui.showToast(result.message, 'warning');
        }
    } catch (error) {
        ui.showToast('撤销失败: ' + error.message, 'error');
    }
}

async function redoAction() {
    try {
        const result = await api.redo();
        if (result.success) {
            ui.showToast('已重做', 'info');
            await loadCurrentImage();
            await loadTypes();
        } else {
            ui.showToast(result.message, 'warning');
        }
    } catch (error) {
        ui.showToast('重做失败: ' + error.message, 'error');
    }
}

// ============ 保存/导出 ============

async function saveProgress() {
    try {
        await api.saveProgress();
        ui.showToast('进度已保存', 'success');
    } catch (error) {
        ui.showToast('保存失败: ' + error.message, 'error');
    }
}

async function exportAnnotations() {
    try {
        const result = await api.exportAnnotations(state.currentType);
        if (result.success) {
            ui.showToast(`导出成功: ${result.data.output_path}`, 'success');
        }
    } catch (error) {
        ui.showToast('导出失败: ' + error.message, 'error');
    }
}

// ============ 启动 ============

document.addEventListener('DOMContentLoaded', init);
