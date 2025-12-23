/**
 * Main Application
 * Connects API, State, and UI.
 */

import { api } from './api.js';
import { store } from './state.js';
import { ui } from './ui.js';

// ============ Logic ============

async function refreshDatasets() {
    try {
        const types = await api.getTypes(true); // fast load first
        store.setState({ datasets: types });
    } catch (err) {
        ui.showToast('无法加载数据类型', 'error');
    }
}

async function selectDataset(name) {
    if (store.getState().currentDataset === name) return;

    store.updateDataset(name);
    ui.setHeader(name);

    // Find target stats for this dataset
    const dataset = store.getState().datasets.find(d => d.name === name);
    if (dataset && dataset.target_count) {
        store.updateStats({
            targetWatermarked: dataset.target_count.watermarked || 0,
            targetNoWatermarked: dataset.target_count.non_watermarked || 0
        });
    }

    await loadCurrentImage();
    await updateProgress(); // Fetch real progress from API
}

async function loadCurrentImage() {
    const dataset = store.getState().currentDataset;
    if (!dataset) return;

    store.setLoading(true);
    try {
        // Get metadata
        const info = await api.getCurrentImage(dataset);

        // Get image data
        const imageData = await api.getImageBase64(dataset, info.index);

        store.updateImage({
            data: imageData.base64,
            path: info.path,
            index: info.index,
            status: info.status
        });

    } catch (err) {
        console.error(err);
        // If it's a 404 or index error, it might mean empty dataset or end
        store.updateImage({ data: null, path: null });
    } finally {
        store.setLoading(false);
    }
}

async function updateProgress() {
    const dataset = store.getState().currentDataset;
    if (!dataset) return;

    try {
        const progress = await api.getProgress(dataset);
        // progress: { total_images, annotated_count, watermarked_count, non_watermarked_count, ... }

        store.updateStats({
            watermarked: progress.watermarked_count,
            noWatermarked: progress.non_watermarked_count
        });

        store.updateImage({
            total: progress.total_images
        });

    } catch (err) {
        // Silent fail for stats
    }
}

// ============ Actions ============

async function handleAnnotation(label) {
    // Label: 1 (Watermarked), 0 (No Watermark)
    // Visual Feedback
    const btnId = label === 1 ? 'btn-watermarked' : 'btn-no-watermarked';
    ui.highlightButton(btnId);

    const state = store.getState();
    if (!state.currentDataset || !state.image.path) {
        ui.showToast('请先选择数据类型', 'warning');
        return;
    }

    try {
        await api.createAnnotation(state.image.path, label, state.currentDataset);

        const labelText = label === 1 ? '有水印' : '无水印';
        ui.showToast(`已标记: ${labelText}`, label === 1 ? 'error' : 'success'); // Error color for red/watermark, Success for green

        // Optimistic update could go here, but let's just go next
        await api.navigateNext(state.currentDataset);
        await loadCurrentImage();
        await updateProgress();

    } catch (err) {
        ui.showToast(`操作失败: ${err.message}`, 'error');
    }
}

async function handleSkip() {
    ui.highlightButton('btn-skip');
    const state = store.getState();
    if (!state.currentDataset || !state.image.path) return;

    try {
        await api.skipImage(state.image.path, state.currentDataset);
        ui.showToast('已跳过', 'info');
        await api.navigateNext(state.currentDataset);
        await loadCurrentImage();
    } catch (err) {
        ui.showToast(`跳过失败: ${err.message}`, 'error');
    }
}

async function handleDelete() {
    const state = store.getState();
    if (!state.currentDataset || !state.image.path) return;

    if (!confirm('确定要从磁盘删除这张图片吗？此操作不可恢复。')) return;

    try {
        await api.deleteImage(state.currentDataset, state.image.path);
        ui.showToast('图片已删除', 'success');
        // Refresh list might be needed if it was the last one, but loadCurrentImage handles errors
        await loadCurrentImage();
        await updateProgress();
    } catch (err) {
        ui.showToast(`删除失败: ${err.message}`, 'error');
    }
}

async function handleNavigate(direction) {
    const dataset = store.getState().currentDataset;
    if (!dataset) return;

    try {
        if (direction === 'next') await api.navigateNext(dataset);
        else await api.navigatePrev(dataset);

        await loadCurrentImage();
    } catch (err) {
        ui.showToast('无法导航', 'error');
    }
}

async function handleUndo() {
    try {
        const res = await api.undo();
        if (res.success) {
            ui.showToast('撤销成功', 'info');
            await loadCurrentImage();
            await updateProgress();
        } else {
            ui.showToast(res.message, 'warning');
        }
    } catch (err) {
        ui.showToast('撤销失败', 'error');
    }
}

async function handleSave() {
    try {
        await api.saveProgress();
        ui.showToast('进度已保存', 'success');
    } catch (err) {
        ui.showToast('保存失败', 'error');
    }
}

async function handleExport() {
    const dataset = store.getState().currentDataset;
    try {
        const res = await api.exportAnnotations(dataset);
        if (res.success) {
            ui.showToast(`导出成功: ${res.data.output_path}`, 'success');
        }
    } catch (err) {
        ui.showToast('导出失败', 'error');
    }
}

async function createNewDataset() {
    const data = ui.getModalData();
    if (!data.name || data.dirs.length === 0) {
        ui.showToast('请填写名称和图片目录', 'warning');
        return;
    }

    try {
        await api.createType({
            name: data.name,
            image_dirs: data.dirs,
            exclude_dirs: data.exclude,
            recursive: data.recursive,
            target_count: {
                watermarked: data.targetWm,
                non_watermarked: data.targetNwm
            },
        });

        ui.showToast('创建成功', 'success');
        ui.toggleModal(false);
        await refreshDatasets();
        selectDataset(data.name);
    } catch (err) {
        ui.showToast(err.message, 'error');
    }
}

// ============ Event Bindings ============

function bindEvents() {
    // Sidebar Dataset Selection
    window.addEventListener('dataset-select', (e) => selectDataset(e.detail));

    // Navbar Buttons
    document.getElementById('btn-export').onclick = handleExport;

    // Toolbar Buttons
    document.getElementById('btn-delete').onclick = handleDelete;
    document.getElementById('btn-prev').onclick = () => handleNavigate('prev');
    document.getElementById('btn-next').onclick = () => handleNavigate('next');
    document.getElementById('btn-undo').onclick = handleUndo;

    // Action Buttons
    document.getElementById('btn-watermarked').onclick = () => handleAnnotation(1);
    document.getElementById('btn-no-watermarked').onclick = () => handleAnnotation(0);
    document.getElementById('btn-skip').onclick = handleSkip;

    // Modal
    const safeBind = (id, fn) => {
        const el = document.getElementById(id);
        if (el) {
            console.log(`Binding click event to ${id}`);
            el.addEventListener('click', (e) => {
                console.log(`Clicked ${id}`);
                fn(e);
            });
        } else {
            console.warn(`Element ${id} not found for binding`);
        }
    };

    safeBind('btn-add-type', () => {
        console.log('Open modal via Add button');
        ui.toggleModal(true);
    });
    safeBind('btn-manage', () => {
        console.log('Open modal via Manage button');
        ui.toggleModal(true);
    });

    safeBind('modal-close', () => ui.toggleModal(false));
    safeBind('modal-cancel', () => ui.toggleModal(false));
    safeBind('modal-save', createNewDataset);

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
            case '1':
            case 'w':
            case 'a': // New: A for Watermarked
                handleAnnotation(1);
                break;
            case '2':
            case 'n':
            case 'd': // New: D for No Watermarked
                handleAnnotation(0);
                break;
            case 's':
                handleSkip();
                break;
            case 'x':
            case 'delete':
                handleDelete();
                break;
            case 'arrowright':
                // case 'd': // Removed D from Next
                handleNavigate('next');
                break;
            case 'arrowleft':
                // case 'a': // Removed A from Prev
                handleNavigate('prev');
                break;
            case 'z':
                if (e.ctrlKey || e.metaKey) handleUndo();
                break;
            case 's':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    handleSave();
                }
                break;
        }
    });

    // Store Subscriptions
    store.subscribe((state) => {
        ui.renderDatasetList(state.datasets, state.currentDataset);
        ui.updateImageDisplay(state.image);
        ui.updateStats(state.stats);
    });

    // Init Zoom
    ui.initZoom();
}

// ============ Init ============
(async function init() {
    bindEvents();
    await refreshDatasets();
    ui.showToast('Watermark Tool Ready', 'info');
})();
