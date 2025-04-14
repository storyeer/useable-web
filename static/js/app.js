/**
 * 主应用脚本
 */

// 在页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('应用初始化...');
    setupHistoryButton();
});

/**
 * 设置历史记录按钮
 */
function setupHistoryButton() {
    // 查找导航栏中的历史按钮
    let historyBtn = document.getElementById('nav-history');
    
    // 如果找不到，可能需要创建一个
    if (!historyBtn) {
        console.log('创建历史记录按钮...');
        
        // 查找导航栏
        const navbar = document.querySelector('.vertical-nav') || document.querySelector('nav');
        
        if (navbar) {
            // 创建历史按钮
            historyBtn = document.createElement('a');
            historyBtn.id = 'nav-history';
            historyBtn.className = 'nav-item';
            historyBtn.href = '#';
            historyBtn.innerHTML = '<i class="fas fa-history"></i><span>历史记录</span>';
            
            // 添加到导航栏
            navbar.appendChild(historyBtn);
            console.log('历史记录按钮已创建');
        } else {
            console.error('找不到导航栏，无法创建历史记录按钮');
        }
    }
}

// 添加脚本引用函数
function loadScript(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// 加载历史管理器脚本
loadScript('/static/js/history-manager.js')
    .then(() => console.log('历史记录管理器加载成功'))
    .catch(err => console.error('加载历史记录管理器失败:', err)); 