/**
 * State Management
 * Simple Store pattern to manage application state and notify subscribers.
 */

class Store {
    constructor() {
        this.state = {
            currentDataset: null,      // Name of the current dataset type
            datasets: [],              // List of all dataset types

            image: {
                data: null,            // Base64 data
                path: null,            // File path
                index: 0,              // Current index
                total: 0,              // Total images
                status: 'pending',     // pending, watermarked, no_watermark, skipped
            },

            stats: {
                watermarked: 0,
                noWatermarked: 0,
                targetWatermarked: 0,
                targetNoWatermarked: 0,
            },

            isLoading: false,
        };

        this.listeners = new Set();
    }

    getState() {
        return this.state;
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    // Update only specific parts of state
    updateDataset(datasetName) {
        this.setState({ currentDataset: datasetName });
    }

    updateImage(imageInfo) {
        this.setState({
            image: { ...this.state.image, ...imageInfo }
        });
    }

    updateStats(stats) {
        this.setState({
            stats: { ...this.state.stats, ...stats }
        });
    }

    setLoading(loading) {
        this.setState({ isLoading: loading });
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
}

export const store = new Store();
