/**
 * AutoPlatform 管理后台通用脚本
 */

// 全局工具函数
const AdminUtils = {
    // 格式化日期
    formatDate: (dateStr) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // 截断文本
    truncate: (text, maxLength = 50) => {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // 复制到剪贴板
    copyToClipboard: async (text) => {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('复制失败:', err);
            return false;
        }
    },
    
    // 显示提示
    showToast: (message, type = 'info') => {
        // 创建提示元素
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // 样式
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // 3秒后移除
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    // API 请求封装
    api: {
        get: async (url) => {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        },
        
        post: async (url, data) => {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            return response.json();
        },
        
        put: async (url, data) => {
            const response = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            return response.json();
        },
        
        delete: async (url) => {
            const response = await fetch(url, { method: 'DELETE' });
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            return response.json();
        }
    }
};

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// 全局暴露
window.AdminUtils = AdminUtils;
