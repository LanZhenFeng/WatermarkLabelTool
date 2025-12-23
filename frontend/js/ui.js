/**
 * UI Controller
 * Handles all DOM updates and interactions.
 */

const elements = {
    datasetList: document.getElementById('dataset-list'),

    // Main Content
    currentDatasetName: document.getElementById('current-dataset-name'),
    currentImageName: document.getElementById('current-image-name'),

    // Image Viewer
    imageWrapper: document.getElementById('image-wrapper'),
    mainImage: document.getElementById('main-image'),
    emptyState: document.getElementById('empty-state'),
    loadingSpinner: document.getElementById('loading-spinner'),

    // Stats
    statWm: document.getElementById('stat-wm'),
    statNwm: document.getElementById('stat-nwm'),
    statsGroup: document.getElementById('stats-group'),
    statPillWm: document.querySelector('.stat-pill.watermarked'),
    statPillNwm: document.querySelector('.stat-pill.no-watermarked'),

    // Counter
    counterCurrent: document.querySelector('#image-counter .current'),
    counterTotal: document.querySelector('#image-counter .total'),

    // Toasts
    toastContainer: document.getElementById('toast-container'),

    // Modal
    datasetModal: document.getElementById('dataset-modal'),
    modalForm: document.getElementById('dataset-form'),
};

export const ui = {
    /**
     * Render the list of datasets in the sidebar
     */
    renderDatasetList(datasets, currentName) {
        elements.datasetList.innerHTML = '';

        if (datasets.length === 0) {
            elements.datasetList.innerHTML = '<div style="padding: 1rem; color: #64748b; font-size: 0.9rem; text-align: center;">暂无数据类型</div>';
            return;
        }

        datasets.sort((a, b) => (b.priority || 0) - (a.priority || 0));

        datasets.forEach(dataset => {
            const el = document.createElement('div');
            el.className = `dataset-item ${dataset.name === currentName ? 'active' : ''}`;
            el.onclick = () => window.dispatchEvent(new CustomEvent('dataset-select', { detail: dataset.name }));

            el.innerHTML = `
                <div class="dataset-info">
                    <span class="dataset-name">${dataset.name}</span>
                </div>
            `;
            elements.datasetList.appendChild(el);
        });
    },

    /**
     * Update the main image display
     */
    updateImageDisplay(imageState) {
        const { data, path, status, index, total } = imageState;

        // Counter
        elements.counterCurrent.textContent = total > 0 ? index + 1 : 0;
        elements.counterTotal.textContent = total;

        // Path Name
        if (path) {
            const filename = path.split(/[/\\]/).pop(); // Simple basename
            elements.currentImageName.textContent = filename;
        } else {
            elements.currentImageName.textContent = '-';
        }

        // Image Content
        if (data) {
            elements.mainImage.src = `data:image/jpeg;base64,${data}`;
            elements.mainImage.classList.remove('hidden');
            elements.emptyState.classList.add('hidden');

            // Reset Zoom
            this.resetZoom();
        } else {
            elements.mainImage.classList.add('hidden');
            if (total === 0) {
                elements.emptyState.classList.remove('hidden');
            }
        }
    },

    // Zoom & Pan State
    transform: { scale: 1, x: 0, y: 0 },
    isDragging: false,
    startX: 0,
    startY: 0,

    resetZoom() {
        this.transform = { scale: 1, x: 0, y: 0 };
        this.applyTransform();
    },

    applyTransform() {
        elements.mainImage.style.transform = `translate(${this.transform.x}px, ${this.transform.y}px) scale(${this.transform.scale})`;
    },

    initZoom() {
        const wrapper = elements.imageWrapper;

        // Wheel Zoom
        wrapper.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = Math.max(0.1, Math.min(10, this.transform.scale * delta)); // Limit zoom 0.1x to 10x

            this.transform.scale = newScale;
            this.applyTransform();
        });

        // Drag - Mouse Down
        wrapper.addEventListener('mousedown', (e) => {
            if (e.target.parentElement.classList.contains('empty-state')) return; // Don't drag empty state
            this.isDragging = true;
            this.startX = e.clientX - this.transform.x;
            this.startY = e.clientY - this.transform.y;
            wrapper.classList.add('grabbing');
        });

        // Drag - Mouse Move
        window.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            e.preventDefault(); // Prevent text selection
            this.transform.x = e.clientX - this.startX;
            this.transform.y = e.clientY - this.startY;
            this.applyTransform();
        });

        // Drag - Mouse Up
        window.addEventListener('mouseup', () => {
            this.isDragging = false;
            wrapper.classList.remove('grabbing');
        });
    },

    updateStats(stats) {
        const { watermarked, noWatermarked, targetWatermarked, targetNoWatermarked } = stats;

        elements.statWm.textContent = `${watermarked}/${targetWatermarked}`;
        elements.statNwm.textContent = `${noWatermarked}/${targetNoWatermarked}`;

        // Visual cues for completion
        if (targetWatermarked > 0 && watermarked >= targetWatermarked) {
            elements.statPillWm.classList.add('complete');
        } else {
            elements.statPillWm.classList.remove('complete');
        }

        if (targetNoWatermarked > 0 && noWatermarked >= targetNoWatermarked) {
            elements.statPillNwm.classList.add('complete');
        } else {
            elements.statPillNwm.classList.remove('complete');
        }
    },

    setLoading(isLoading) {
        if (isLoading) {
            elements.loadingSpinner.classList.remove('hidden');
        } else {
            elements.loadingSpinner.classList.add('hidden');
        }
    },

    setHeader(datasetName) {
        elements.currentDatasetName.textContent = datasetName || "请选择数据类型";
        if (!datasetName) {
            elements.currentImageName.textContent = "-";
            elements.statsGroup.style.opacity = '0.5';
        } else {
            elements.statsGroup.style.opacity = '1';
        }
    },

    /**
     * Toast Notifications
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '❌';
        if (type === 'warning') icon = '⚠️';

        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
        `;

        elements.toastContainer.appendChild(toast);

        // Remove after 3s
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Modal
     */
    toggleModal(show) {
        if (show) {
            elements.datasetModal.classList.add('active');
        } else {
            elements.datasetModal.classList.remove('active');
            elements.modalForm.reset();
        }
    },

    getModalData() {
        const name = document.getElementById('input-name').value.trim();
        const dirs = document.getElementById('input-dirs').value.trim().split('\n').filter(s => s.trim());
        const exclude = document.getElementById('input-exclude').value.trim().split('\n').filter(s => s.trim());
        const recursive = document.getElementById('input-recursive').checked;

        const targetWm = parseInt(document.getElementById('input-target-wm').value) || 0;
        const targetNwm = parseInt(document.getElementById('input-target-nwm').value) || 0;

        return { name, dirs, exclude, recursive, targetWm, targetNwm };
    },

    /**
     * Trigger a visual highlight on a button
     */
    highlightButton(id) {
        const btn = document.getElementById(id);
        if (btn) {
            // Remove first to reset if clicked rapidly
            btn.classList.remove('active-key');
            // Force reflow
            void btn.offsetWidth;
            btn.classList.add('active-key');
            setTimeout(() => btn.classList.remove('active-key'), 150);
        }
    },

    /**
     * Manage Modal
     */
    toggleManageModal(show) {
        const modal = document.getElementById('manage-modal');
        if (show) {
            modal.classList.add('active');
        } else {
            modal.classList.remove('active');
        }
    },

    renderManageList(datasets, onEdit, onDelete) {
        const list = document.getElementById('manage-list');
        if (!list) return;

        if (datasets.length === 0) {
            list.innerHTML = '<div style="padding: 1rem; color: var(--text-muted); text-align: center;">暂无数据类型</div>';
            return;
        }

        list.innerHTML = datasets.map(d => {
            const dirs = d.image_dirs || [];
            const dirInfo = dirs.length === 1 ? dirs[0].split('/').slice(-2).join('/') : `${dirs.length} 个目录`;
            return `
            <div class="manage-item" data-name="${d.name}">
                <div class="manage-item-info">
                    <div class="manage-item-name">${d.name}</div>
                    <div class="manage-item-path">${dirInfo}</div>
                </div>
                <div class="manage-item-actions">
                    <button class="btn btn-sm btn-secondary" data-action="edit">编辑</button>
                    <button class="btn btn-sm btn-danger" data-action="delete">删除</button>
                </div>
            </div>
            `;
        }).join('');

        // Bind events
        list.querySelectorAll('[data-action="edit"]').forEach(btn => {
            btn.onclick = () => onEdit(btn.closest('.manage-item').dataset.name);
        });
        list.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.onclick = () => onDelete(btn.closest('.manage-item').dataset.name);
        });
    },

    /**
     * Fill edit modal with existing data
     */
    fillModalForEdit(dataset) {
        document.getElementById('input-name').value = dataset.name;
        document.getElementById('input-name').disabled = true; // Can't change name
        document.getElementById('input-dirs').value = (dataset.image_dirs || []).join('\n');
        document.getElementById('input-exclude').value = (dataset.exclude_dirs || []).join('\n');
        document.getElementById('input-recursive').checked = dataset.recursive !== false;
        document.getElementById('input-target-wm').value = (dataset.target_count && dataset.target_count.watermarked) || 0;
        document.getElementById('input-target-nwm').value = (dataset.target_count && dataset.target_count.non_watermarked) || 0;
    },

    resetModalForNew() {
        document.getElementById('input-name').disabled = false;
        elements.modalForm.reset();
    }
};
