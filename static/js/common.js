/**
 * 通用功能模块
 */

// 防止 gtag 未定义错误
window.gtag = window.gtag || function(){};

// 通用工具函数
const utils = {
    // 格式化日期
    formatDate(date) {
        return new Date(date).toLocaleString();
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 简单的错误处理
    handleError(error) {
        console.error('Error:', error);
        // 可以添加更多错误处理逻辑
    }
};

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 获取所有需要的 DOM 元素
    const elements = {
        toggleSidebarBtn: document.getElementById('toggleSidebarBtn'),
        historySidebar: document.getElementById('history-sidebar'),
        chatMain: document.querySelector('.chat-main'),
        toggleChatBtn: document.getElementById('toggle-chat-btn'),
        toggleHistoryBtn: document.getElementById('toggle-history-btn'),
        chatContainer: document.getElementById('chat-container'),
        chatInput: document.getElementById('chat-input'),
        sendButton: document.getElementById('send-button')
    };

    // 侧边栏切换功能
    if (elements.toggleSidebarBtn && elements.historySidebar && elements.chatMain) {
        elements.toggleSidebarBtn.addEventListener('click', () => {
            elements.historySidebar.classList.toggle('active');
            elements.chatMain.classList.toggle('sidebar-active');
        });
    }

    // 聊天和历史记录切换功能
    if (elements.toggleChatBtn && elements.chatContainer) {
        // 初始状态设置
        if (elements.chatContainer.style.display !== 'none') {
            elements.toggleChatBtn.classList.add('active');
        }

        elements.toggleChatBtn.addEventListener('click', () => {
            elements.chatContainer.style.display = '';
            elements.historySidebar.style.display = 'none';
            elements.toggleChatBtn.classList.add('active');
            elements.toggleHistoryBtn.classList.remove('active');
        });
    }

    if (elements.toggleHistoryBtn && elements.historySidebar) {
        elements.toggleHistoryBtn.addEventListener('click', () => {
            elements.historySidebar.style.display = '';
            elements.chatContainer.style.display = 'none';
            elements.toggleHistoryBtn.classList.add('active');
            elements.toggleChatBtn.classList.remove('active');
        });
    }

    // 聊天输入处理
    if (elements.chatInput && elements.sendButton && elements.chatContainer) {
        elements.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                elements.sendButton.click();
            }
        });
    }

    // 初始化导航管理器
    if (typeof NavManager === 'function') {
        window.navManager = new NavManager();
    }
});

// 导出工具函数
export default utils;

// 添加到common.js文件开头
console.log("Common.js 已加载");

// 错误处理
window.onerror = function(message, source, lineno, colno, error) {
    console.error("JavaScript错误:", message, "at", source, ":" + lineno);
    // 创建错误提示
    const errorDiv = document.createElement('div');
    errorDiv.style = "position:fixed;top:0;left:0;background:red;color:white;padding:10px;z-index:9999;width:100%;";
    errorDiv.textContent = "错误: " + message;
    document.body.appendChild(errorDiv);
    return true;
};

// 设置当前活动页面的导航链接高亮
document.addEventListener('DOMContentLoaded', function() {
    console.log("页面DOM已加载");
    
    // 检查并初始化用户导航
    if (typeof initUserNavItem === 'function') {
        initUserNavItem();
    } else if (typeof updateUserNavItem === 'function') {
        // 兼容旧代码
        updateUserNavItem();
    }
    
    // 检查是否访问受保护页面
    checkAuthForCurrentPage();
    
    // 如果用户已登录，更新相关UI
    const isLoggedIn = !!localStorage.getItem('token');
    if (isLoggedIn) {
        console.log("用户已登录");
        try {
            const userData = JSON.parse(localStorage.getItem('user') || '{}');
            console.log("用户信息:", userData.username);
        } catch (e) {
            console.error("解析用户数据失败");
        }
    } else {
        console.log("用户未登录");
    }
    
    // 添加调试信息
    const debugDiv = document.createElement('div');
    debugDiv.style = "position:fixed;top:10px;right:10px;background:green;color:white;padding:5px;z-index:9999;";
    debugDiv.textContent = "页面已加载: " + new Date().toLocaleTimeString();
    document.body.appendChild(debugDiv);
    
    // 显示布局信息
    console.log("导航栏:", document.querySelector('.vertical-nav'));
    console.log("聊天界面:", document.querySelector('.chat-interface'));
    console.log("欢迎卡片:", document.querySelector('.welcome-card'));
    
    // 获取当前路径
    const path = window.location.pathname;
    
    // 移除所有导航链接的active类
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // 根据路径设置相应链接的active类
    if (path === '/' || path === '/index') {
        document.getElementById('nav-home').classList.add('active');
    } else if (path === '/knowledge') {
        document.getElementById('nav-knowledge').classList.add('active');
    } else if (path === '/contact') {
        document.getElementById('nav-contact').classList.add('active');
    }
    
    // 用户状态处理代码
    handleUserStatus();

    // 只在开发环境显示
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        const refreshButton = document.createElement('button');
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
        refreshButton.title = '强制刷新所有资源';
        refreshButton.classList.add('dev-refresh-button');
        refreshButton.onclick = function() {
            // 强制刷新，绕过缓存
            window.location.reload(true);
            // 清除localStorage中的缓存版本标记
            localStorage.removeItem('resource_version');
        };
        
        document.body.appendChild(refreshButton);
    }

    // 版本检查 - 从meta标签获取版本号
    const metaVersion = document.querySelector('meta[name="resource-version"]');
    if (metaVersion) {
        const currentVersion = metaVersion.getAttribute('content');
        const storedVersion = localStorage.getItem('resource_version');
        
        // 存储当前版本
        localStorage.setItem('resource_version', currentVersion);
        
        // 如果版本不匹配且不是第一次访问，提示刷新
        if (storedVersion && storedVersion !== currentVersion) {
            const refreshNotice = document.createElement('div');
            refreshNotice.className = 'version-refresh-notice';
            refreshNotice.innerHTML = `
                <p>网站已更新，请刷新页面获取最新内容</p>
                <button id="refreshPageBtn">立即刷新</button>
            `;
            document.body.appendChild(refreshNotice);
            
            document.getElementById('refreshPageBtn').addEventListener('click', function() {
                window.location.reload(true);
            });
        }
    }

    // 处理游客模式初始化
    if (document.querySelector('meta[name="set-guest-mode"]')) {
        localStorage.setItem('guest_mode', 'true');
    }
    
    // 如果是首页且是游客模式，显示正确的界面
    const isHomePage = window.location.pathname === '/' || window.location.pathname === '/index'; 
    const isGuest = localStorage.getItem('guest_mode') === 'true';
    
    if (isHomePage && isGuest) {
        // 隐藏侧边栏，显示主页内容
        const historySidebar = document.getElementById('history-sidebar');
        if (historySidebar) historySidebar.style.display = 'none';
        
        // 显示主页内容区
        const homeContent = document.getElementById('home-content');
        if (homeContent) homeContent.style.display = 'block';
        
        // 设置页面布局为主页样式
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) chatContainer.classList.add('home-layout');
        
        // 更新导航状态
        handleUserStatus(); // 确保显示游客状态
    }

    // 确保页面平滑加载
    document.body.classList.add('loaded');
    
    // 垂直导航栏激活当前页面项
    const currentPath = window.location.pathname;
    document.querySelectorAll('.vertical-nav .nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href === currentPath || 
            (href !== '/' && currentPath.startsWith(href)) ||
            (href === '/' && currentPath === '/')) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    checkProtectedPage();

    // 在访客退出后检查并跳转
    checkGuestLogout();

    // 修复用户头像提示
    const loginAvatar = document.querySelector('.login-avatar');
    if (loginAvatar) {
        // 确保title属性正确设置
        loginAvatar.setAttribute('title', '点击登录');
        
        // 移除任何可能的错误事件监听器
        loginAvatar.removeAttribute('placeholder');
        loginAvatar.removeAttribute('data-placeholder');
    }
});

// 处理用户登录状态
function handleUserStatus() {
    const authButtons = document.getElementById('auth-buttons');
    const userDropdown = document.getElementById('user-dropdown');
    
    if (!authButtons || !userDropdown) return;
    
    const token = localStorage.getItem('token');
    const userString = localStorage.getItem('user');
    const isGuest = localStorage.getItem('guest_mode') === 'true';
    
    if (token && userString && !isGuest) {
        // 已登录状态
        const user = JSON.parse(userString);
        
        if (authButtons) authButtons.style.display = 'none';
        if (userDropdown) userDropdown.style.display = 'flex';
        
        // 设置用户信息
        setUserInfo(user);
        
    } else if (isGuest) {
        // 访客模式
        if (authButtons) authButtons.style.display = 'none';
        if (userDropdown) userDropdown.style.display = 'flex';
        
        // 设置访客信息
        setGuestInfo();
        
    } else {
        // 未登录状态
        if (authButtons) authButtons.style.display = 'flex';
        if (userDropdown) userDropdown.style.display = 'none';
    }
}

// 设置登录用户信息
function setUserInfo(user) {
    const avatarElem = document.getElementById('user-avatar');
    const usernameElem = document.getElementById('username-display');
    const roleElem = document.getElementById('user-role');
    
    if (avatarElem && user.username) {
        avatarElem.textContent = user.username.charAt(0).toUpperCase();
    }
    
    if (usernameElem && user.username) {
        usernameElem.textContent = user.username;
    }
    
    if (roleElem && user.role) {
        roleElem.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    } else if (roleElem) {
        roleElem.textContent = '用户';
    }
    
    // 添加退出登录事件
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('guest_mode');
            window.location.reload();
        });
    }
}

// 设置访客信息
function setGuestInfo() {
    const avatarElem = document.getElementById('user-avatar');
    const usernameElem = document.getElementById('username-display');
    const roleElem = document.getElementById('user-role');
    
    if (avatarElem) {
        avatarElem.textContent = 'G';
    }
    
    if (usernameElem) {
        usernameElem.textContent = '游客';
    }
    
    if (roleElem) {
        roleElem.textContent = '访客模式';
    }
    
    // 添加退出游客模式事件
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.textContent = '退出访客模式';
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('guest_mode');
            window.location.reload();
        });
    }
}

// 检查是否需要登录才能访问当前页面
function checkProtectedPage() {
    const protectedPaths = ['/profile', '/chat/'];
    const currentPath = window.location.pathname;
    
    // 检查当前路径是否是受保护的
    const isProtected = protectedPaths.some(path => 
        currentPath === path || currentPath.startsWith(path)
    );
    
    if (isProtected && !localStorage.getItem('token')) {
        // 保存当前URL以便登录后跳转回来
        sessionStorage.setItem('redirectAfterLogin', currentPath);
        // 跳转到登录页
        window.location.href = '/login';
        return false;
    }
    
    return true;
}

// 检查当前页面是否需要登录
function checkAuthForCurrentPage() {
    const protectedPaths = ['/profile', '/chat/'];
    const currentPath = window.location.pathname;
    
    // 检查是否在保护路径下
    const isProtected = protectedPaths.some(path => 
        currentPath === path || 
        (path.endsWith('/') && currentPath.startsWith(path))
    );
    
    // 若在保护路径下且未登录，则重定向
    if (isProtected) {
        const isLoggedIn = !!localStorage.getItem('token');
        const isGuest = localStorage.getItem('guest_mode') === 'true';
        
        if (!isLoggedIn && !isGuest) {
            console.log("访问受保护页面但未登录，重定向到登录页");
            // 保存当前URL以便登录后返回
            sessionStorage.setItem('redirectAfterLogin', currentPath);
            window.location.href = '/login';
            return false;
        }
    }
    
    return true;
}

// 在访客退出后检查并跳转
function checkGuestLogout() {
    // 检查URL参数是否包含guest_logout=true
    const urlParams = new URLSearchParams(window.location.search);
    const guestLogout = urlParams.get('guest_logout');
    
    if (guestLogout === 'true') {
        console.log("检测到访客退出参数");
        // 移除本地存储的访客标记
        localStorage.removeItem('guest_mode');
        
        // 清除URL参数
        window.history.replaceState(null, '', window.location.pathname);
        
        // 如果当前不是登录页，则跳转到登录页
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }
} 