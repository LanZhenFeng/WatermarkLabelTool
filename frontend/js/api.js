/**
 * API Client
 * Wraps all backend calls. Matches the original API structure.
 */

const API_BASE = '/api';

class ApiClient {
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Network Error' }));
                throw new Error(errorData.detail || `Request failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // ============ Types ============
    async getTypes(skipScan = false) {
        return this.request(`/types?skip_scan=${skipScan}`);
    }

    async createType(data) {
        return this.request('/types', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async updateType(name, data) {
        // Construct query params for partial updates if needed, 
        // but original passed params in query. Let's stick to body if possible or mirror exactly.
        // Original: request(\`/types/\${encodeURIComponent(name)}?\${params}\`, { method: 'PUT' });
        // It seems the original passed data as query params? 
        // Let's re-read the original code snippet.
        // Original:
        // const params = new URLSearchParams();
        // Object.entries(data).forEach...
        // return request(..., method: 'PUT')

        // Use URLSearchParams for compatibility
        const params = new URLSearchParams();
        Object.entries(data).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                params.append(key, value);
            }
        });

        return this.request(`/types/${encodeURIComponent(name)}?${params.toString()}`, {
            method: 'PUT'
        });
    }

    async deleteType(name) {
        return this.request(`/types/${encodeURIComponent(name)}`, {
            method: 'DELETE',
        });
    }

    // ============ Images ============
    async getCurrentImage(datasetType) {
        return this.request(`/images/current?dataset_type=${encodeURIComponent(datasetType)}`);
    }

    async getImageByIndex(datasetType, index) {
        return this.request(`/images/${index}?dataset_type=${encodeURIComponent(datasetType)}`);
    }

    async getImageBase64(datasetType, index) {
        return this.request(`/images/base64/${index}?dataset_type=${encodeURIComponent(datasetType)}`);
    }

    async deleteImage(datasetType, imagePath) {
        return this.request(`/images/delete?dataset_type=${encodeURIComponent(datasetType)}&image_path=${encodeURIComponent(imagePath)}`, {
            method: 'DELETE',
        });
    }

    // ============ Annotations ============
    async createAnnotation(imagePath, label, datasetType) {
        return this.request('/annotations', {
            method: 'POST',
            body: JSON.stringify({
                image_path: imagePath,
                label: label,
                dataset_type: datasetType,
            }),
        });
    }

    async skipImage(imagePath, datasetType) {
        return this.request(`/annotations/skip?dataset_type=${encodeURIComponent(datasetType)}&image_path=${encodeURIComponent(imagePath)}`, {
            method: 'POST',
        });
    }

    async undo() {
        return this.request('/annotations/undo', { method: 'POST' });
    }

    async redo() { // Not explicitly in UI plan but good to have
        return this.request('/annotations/redo', { method: 'POST' });
    }

    // ============ Progress & Navigation ============
    async getProgress(datasetType) {
        return this.request(`/progress?dataset_type=${encodeURIComponent(datasetType)}`);
    }

    async saveProgress() {
        return this.request('/progress/save', { method: 'POST' });
    }

    async navigateNext(datasetType) {
        return this.request(`/navigate/next?dataset_type=${encodeURIComponent(datasetType)}`, {
            method: 'POST',
        });
    }

    async navigatePrev(datasetType) {
        return this.request(`/navigate/prev?dataset_type=${encodeURIComponent(datasetType)}`, {
            method: 'POST',
        });
    }

    // ============ Export ============
    async exportAnnotations(datasetType = null) {
        const body = datasetType ? { dataset_type: datasetType } : {};
        return this.request('/export', {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }
}

export const api = new ApiClient();
