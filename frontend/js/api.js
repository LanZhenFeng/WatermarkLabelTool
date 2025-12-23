/**
 * API 调用封装
 */

const API_BASE = '/api';

const api = {
    /**
     * 发送请求
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: '请求失败' }));
            throw new Error(error.detail || '请求失败');
        }

        return response.json();
    },

    // ============ 数据类型管理 ============

    async getTypes(skipScan = false) {
        return this.request(`/types?skip_scan=${skipScan}`);
    },

    async createType(data) {
        return this.request('/types', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    async updateType(name, data) {
        const params = new URLSearchParams();
        Object.entries(data).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                params.append(key, value);
            }
        });
        return this.request(`/types/${encodeURIComponent(name)}?${params}`, {
            method: 'PUT',
        });
    },

    async deleteType(name) {
        return this.request(`/types/${encodeURIComponent(name)}`, {
            method: 'DELETE',
        });
    },

    // ============ 图片管理 ============

    async getImages(datasetType, refresh = false) {
        return this.request(`/images?dataset_type=${encodeURIComponent(datasetType)}&refresh=${refresh}`);
    },

    async getCurrentImage(datasetType) {
        return this.request(`/images/current?dataset_type=${encodeURIComponent(datasetType)}`);
    },

    async getImageByIndex(datasetType, index) {
        return this.request(`/images/${index}?dataset_type=${encodeURIComponent(datasetType)}`);
    },

    async getImageData(datasetType, index) {
        const response = await fetch(`${API_BASE}/images/data/${index}?dataset_type=${encodeURIComponent(datasetType)}`);
        if (!response.ok) {
            throw new Error('图片加载失败');
        }
        return response.blob();
    },

    async getImageBase64(datasetType, index) {
        return this.request(`/images/base64/${index}?dataset_type=${encodeURIComponent(datasetType)}`);
    },

    async deleteImage(datasetType, imagePath) {
        return this.request(`/images/delete?dataset_type=${encodeURIComponent(datasetType)}&image_path=${encodeURIComponent(imagePath)}`, {
            method: 'DELETE',
        });
    },

    // ============ 标注管理 ============

    async createAnnotation(imagePath, label, datasetType) {
        return this.request('/annotations', {
            method: 'POST',
            body: JSON.stringify({
                image_path: imagePath,
                label: label,
                dataset_type: datasetType,
            }),
        });
    },

    async skipImage(imagePath, datasetType) {
        return this.request(`/annotations/skip?dataset_type=${encodeURIComponent(datasetType)}&image_path=${encodeURIComponent(imagePath)}`, {
            method: 'POST',
        });
    },

    async undo() {
        return this.request('/annotations/undo', { method: 'POST' });
    },

    async redo() {
        return this.request('/annotations/redo', { method: 'POST' });
    },

    // ============ 进度管理 ============

    async getProgress(datasetType) {
        return this.request(`/progress?dataset_type=${encodeURIComponent(datasetType)}`);
    },

    async saveProgress() {
        return this.request('/progress/save', { method: 'POST' });
    },

    async getSessionStats() {
        return this.request('/progress/session');
    },

    // ============ 导入导出 ============

    async exportAnnotations(datasetType = null) {
        const data = datasetType ? { dataset_type: datasetType } : {};
        return this.request('/export', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    async getStatistics() {
        return this.request('/export/statistics');
    },

    // ============ 导航 ============

    async navigateNext(datasetType) {
        return this.request(`/navigate/next?dataset_type=${encodeURIComponent(datasetType)}`, {
            method: 'POST',
        });
    },

    async navigatePrev(datasetType) {
        return this.request(`/navigate/prev?dataset_type=${encodeURIComponent(datasetType)}`, {
            method: 'POST',
        });
    },

    async navigateGoto(datasetType, index) {
        return this.request(`/navigate/goto?dataset_type=${encodeURIComponent(datasetType)}&index=${index}`, {
            method: 'POST',
        });
    },
};
