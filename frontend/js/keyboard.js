/**
 * 快捷键处理
 */

const keyboard = {
    /**
     * 初始化快捷键
     */
    init() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    },

    /**
     * 处理按键事件
     */
    handleKeyDown(event) {
        // 如果在输入框中，不处理快捷键
        if (event.target.matches('input, textarea, select')) {
            return;
        }

        const key = event.key.toLowerCase();
        const ctrlOrMeta = event.ctrlKey || event.metaKey;

        // Ctrl/Cmd 组合键
        if (ctrlOrMeta) {
            switch (key) {
                case 'z':
                    event.preventDefault();
                    undoAction();
                    break;
                case 'y':
                    event.preventDefault();
                    redoAction();
                    break;
                case 's':
                    event.preventDefault();
                    saveProgress();
                    break;
            }
            return;
        }

        // 单键快捷键
        switch (key) {
            // 标注有水印
            case '1':
            case 'w':
                event.preventDefault();
                annotate(1);
                break;

            // 标注无水印
            case '2':
            case 'n':
                event.preventDefault();
                annotate(0);
                break;

            // 跳过
            case 's':
                event.preventDefault();
                skipImage();
                break;

            // 删除图片
            case 'x':
            case 'delete':
                event.preventDefault();
                deleteCurrentImage();
                break;

            // 上一张
            case 'a':
            case 'arrowleft':
                event.preventDefault();
                navigatePrev();
                break;

            // 下一张
            case 'd':
            case 'arrowright':
                event.preventDefault();
                navigateNext();
                break;

            // 全屏
            case 'f11':
                event.preventDefault();
                toggleFullscreen();
                break;
        }
    },
};

/**
 * 切换全屏
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            ui.showToast('无法进入全屏: ' + err.message, 'error');
        });
    } else {
        document.exitFullscreen();
    }
}

// 初始化
keyboard.init();
