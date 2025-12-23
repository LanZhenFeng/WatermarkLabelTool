/**
 * UI 组件和工具函数
 */

const ui = {
    /**
     * 显示 Toast 通知
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
        };

        toast.innerHTML = `
            <span>${icons[type] || icons.info}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * 更新状态徽章
     */
    updateStatusBadge(status) {
        const badge = document.getElementById('status-badge');
        const text = document.getElementById('status-text');

        const statusMap = {
            pending: { class: 'pending', text: '待标注' },
            watermarked: { class: 'watermarked', text: '有水印' },
            no_watermark: { class: 'no-watermark', text: '无水印' },
            skipped: { class: 'skipped', text: '已跳过' },
        };

        const config = statusMap[status] || statusMap.pending;
        badge.className = `status-badge ${config.class}`;
        text.textContent = config.text;
    },

    /**
     * 更新进度显示
     */
    updateProgress(current, total) {
        document.getElementById('progress-count').textContent = `${current}/${total}`;
        document.getElementById('current-index').textContent = current + 1;
        document.getElementById('total-images').textContent = total;
    },

    /**
     * 更新文件路径显示
     */
    updateFilePath(path) {
        document.getElementById('current-path').textContent = path || '未选择文件';
    },

    /**
     * 显示图片
     */
    showImage(base64Data) {
        const display = document.getElementById('image-display');
        const placeholder = document.getElementById('image-placeholder');
        const indexDiv = document.getElementById('image-index');

        display.src = `data:image/jpeg;base64,${base64Data}`;
        display.style.display = 'block';
        placeholder.style.display = 'none';
        indexDiv.style.display = 'block';
    },

    /**
     * 隐藏图片
     */
    hideImage() {
        const display = document.getElementById('image-display');
        const placeholder = document.getElementById('image-placeholder');
        const indexDiv = document.getElementById('image-index');

        display.style.display = 'none';
        placeholder.style.display = 'flex';
        indexDiv.style.display = 'none';
    },

    /**
     * 显示加载中
     */
    showLoading() {
        const placeholder = document.getElementById('image-placeholder');
        placeholder.innerHTML = `
            <div class="loading-spinner"></div>
            <p>加载中...</p>
        `;
        placeholder.style.display = 'flex';
        document.getElementById('image-display').style.display = 'none';
    },

    /**
     * 渲染类型列表到侧边栏
     */
    renderTypeList(types, activeType) {
        const list = document.getElementById('type-list');
        list.innerHTML = types.map(type => {
            const target = type.target_count || {};
            const current = type.current_count || {};
            const targetTotal = (target.watermarked || 0) + (target.non_watermarked || 0);
            const currentTotal = (current.watermarked || 0) + (current.non_watermarked || 0);

            // 计算完成状态
            const hasTarget = targetTotal > 0;
            const isComplete = hasTarget && currentTotal >= targetTotal;
            const progressText = hasTarget
                ? `${currentTotal}/${targetTotal}`
                : `${type.annotated_count}/${type.total_images}`;
            const statusIcon = isComplete ? '✅' : '';

            return `
            <li class="type-item ${type.name === activeType ? 'active' : ''} ${isComplete ? 'complete' : ''}" 
                onclick="selectType('${type.name}')">
                <div class="checkbox">${type.name === activeType ? '✓' : ''}</div>
                <span class="name">${type.name} ${statusIcon}</span>
                <span class="count ${isComplete ? 'complete' : ''}">${progressText}</span>
            </li>
        `}).join('');
    },

    /**
     * 渲染类型下拉选择器
     */
    renderTypeSelector(types, activeType) {
        const selector = document.getElementById('dataset-type');
        selector.innerHTML = `
            <option value="">请选择数据类型</option>
            ${types.map(type => `
                <option value="${type.name}" ${type.name === activeType ? 'selected' : ''}>
                    ${type.name} (${type.annotated_count}/${type.total_images})
                </option>
            `).join('')}
        `;
    },

    /**
     * 渲染管理列表
     */
    renderManageList(types) {
        const list = document.getElementById('manage-list');
        if (types.length === 0) {
            list.innerHTML = '<p style="color: var(--text-muted); text-align: center;">暂无数据类型</p>';
            return;
        }

        list.innerHTML = types.map(type => {
            // 截断长路径，只显示最后两层目录
            const pathParts = type.image_dir.split('/').filter(p => p);
            const shortPath = pathParts.length > 2
                ? '.../' + pathParts.slice(-2).join('/')
                : type.image_dir;

            return `
            <div class="manage-item">
                <div class="manage-item-info">
                    <div class="manage-item-name">${type.name}</div>
                    <div class="manage-item-path" title="${type.image_dir}">
                        ${shortPath} · ${type.total_images} 张图片
                    </div>
                </div>
                <div class="manage-item-actions">
                    <button class="btn btn-secondary btn-sm" onclick="editType('${type.name}')">编辑</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteType('${type.name}')">删除</button>
                </div>
            </div>
        `}).join('');
    },
};

// ============ 模态框控制 ============

function showAddTypeModal() {
    document.getElementById('modal-title').textContent = '添加数据类型';
    document.getElementById('type-form').reset();
    document.getElementById('type-name').disabled = false;
    document.getElementById('type-modal').classList.add('active');
    closeManageModal();
}

function closeModal() {
    document.getElementById('type-modal').classList.remove('active');
}

function showManageModal() {
    document.getElementById('manage-modal').classList.add('active');
    refreshManageList();
}

function closeManageModal() {
    document.getElementById('manage-modal').classList.remove('active');
}

async function refreshManageList() {
    try {
        const types = await api.getTypes();
        ui.renderManageList(types);
    } catch (error) {
        ui.showToast('加载失败: ' + error.message, 'error');
    }
}
