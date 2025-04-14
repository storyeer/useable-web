/**
 * 导航栏管理
 * 仅处理导航交互，不创建导航元素
 */

// 创建一个ApiService的fallback实现，确保关键功能即使外部服务不可用也能工作
if (typeof window.ApiService === 'undefined') {
    console.log('创建ApiService fallback');
    window.ApiService = {
        // 获取聊天历史
        getChatHistory: async function() {
            console.log('使用fallback getChatHistory');
            try {
                const response = await fetch('/api/chat/history');
                return await response.json();
            } catch (error) {
                console.error('获取历史记录失败:', error);
                return { success: false, error: error.message };
            }
        },
        
        // 加载对话
        loadConversation: async function(conversationId) {
            console.log('使用fallback loadConversation');
            try {
                const response = await fetch(`/api/chat/conversations/${conversationId}`);
                return await response.json();
            } catch (error) {
                console.error('加载对话失败:', error);
                return { success: false, error: error.message };
            }
        },
        
        // 删除对话
        deleteConversation: async function(conversationId) {
            console.log('使用fallback deleteConversation');
            try {
                const response = await fetch(`/api/chat/conversations/${conversationId}`, {
                    method: 'DELETE'
                });
                return await response.json();
            } catch (error) {
                console.error('删除对话失败:', error);
                return { success: false, error: error.message };
            }
        }
    };
}

// 添加全局导航栏切换函数 - 在文件顶部定义
window.toggleNavBar = function() {
    console.log('全局toggleNavBar被调用');
    const verticalNav = document.querySelector('.vertical-nav');
    if (!verticalNav) {
        console.error('无法找到垂直导航栏元素');
        return;
    }
    
    // 切换expanded类
    verticalNav.classList.toggle('expanded');
    
    // 调整内容区域
    const contentArea = document.querySelector('.content-area');
    if (contentArea) {
        if (verticalNav.classList.contains('expanded')) {
            contentArea.style.paddingLeft = '180px';
        } else {
            contentArea.style.paddingLeft = '60px';
        }
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // 为导航项添加工具提示
    const tooltips = {
        'home': '首页',
        'history-btn': '历史记录',
        'knowledge': '知识库',
        'settings-btn': '设置',
        'contact': '联系我们',
        'user-nav-item': '登录/注册'
    };
    
    // 为每个导航项添加工具提示
    document.querySelectorAll('.nav-item').forEach(item => {
        const id = item.id || item.href.split('/').pop() || 'home';
        if (tooltips[id]) {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.innerText = tooltips[id];
            item.appendChild(tooltip);
        }
    });
    
    // 检查用户登录状态，更新用户图标和链接
    const userNavItem = document.getElementById('user-nav-item');
    if (userNavItem) {
        const isLoggedIn = !!localStorage.getItem('token');
        
        if (isLoggedIn) {
            // 已登录状态
            userNavItem.querySelector('i').classList.remove('fa-user');
            userNavItem.querySelector('i').classList.add('fa-user-check');
            
            // 更新工具提示
            const tooltip = userNavItem.querySelector('.tooltip');
            if (tooltip) {
                tooltip.innerText = '个人资料';
            }
            
            // 点击切换到用户页面
            userNavItem.href = '/profile';
            
            // 添加退出登录选项
            userNavItem.addEventListener('click', function(e) {
                if (!confirm('确定要退出登录吗？')) {
                    e.preventDefault();
                    return;
                }
                
                // 清除登录信息并刷新
                localStorage.removeItem('token');
                window.location.href = '/';
            });
        } else {
            // 未登录状态
            userNavItem.href = '/login';
        }
    }
    
    // 设置按钮点击事件
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', function() {
            // 显示设置面板或跳转到设置页面
            alert('设置功能即将上线');
        });
    }
    
    // 移动设备导航适配
    const mobileNavToggle = document.createElement('button');
    mobileNavToggle.className = 'mobile-nav-toggle';
    mobileNavToggle.innerHTML = '<i class="fas fa-bars"></i>';
    document.body.appendChild(mobileNavToggle);
    
    // 获取导航元素
    const verticalNav = document.querySelector('.vertical-nav');
    
    // 移动端导航切换
    mobileNavToggle.addEventListener('click', function() {
        verticalNav.classList.toggle('visible');
        this.innerHTML = verticalNav.classList.contains('visible') ? 
            '<i class="fas fa-times"></i>' : '<i class="fas fa-bars"></i>';
    });
    
    // 点击导航项后在移动端自动隐藏导航栏
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                verticalNav.classList.remove('visible');
                mobileNavToggle.innerHTML = '<i class="fas fa-bars"></i>';
            }
        });
    });
    
    // 设置当前活动页面的导航高亮
    const path = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        // 移除所有活动类
        item.classList.remove('active');
        
        // 根据路径匹配设置活动类
        const href = item.getAttribute('href');
        if (href === path || 
            (href !== '/' && path.startsWith(href)) || 
            (href === '/' && path === '/index.html')) {
            item.classList.add('active');
        }
    });
    
    // 历史记录按钮点击处理
    const historyBtn = document.querySelector('.nav-item[title="历史记录"]') || document.getElementById('nav-history');
    const historySidebar = document.getElementById('history-sidebar');
    const historyOverlay = document.getElementById('history-overlay');
    
    if (historyBtn && historySidebar) {
        historyBtn.addEventListener('click', (e) => {
            e.preventDefault();
            historySidebar.classList.toggle('active');
            if (historyOverlay) {
                historyOverlay.classList.toggle('active');
            }
            
            // 加载历史记录
            if (historySidebar.classList.contains('active')) {
                loadChatHistory();
            }
        });

        // 关闭按钮点击处理
        const closeBtn = historySidebar.querySelector('.close-history') || historySidebar.querySelector('.history-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                historySidebar.classList.remove('active');
                if (historyOverlay) {
                    historyOverlay.classList.remove('active');
                }
            });
        }

        // 点击遮罩层关闭
        if (historyOverlay) {
            historyOverlay.addEventListener('click', () => {
                historySidebar.classList.remove('active');
                historyOverlay.classList.remove('active');
            });
        }
        
        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && historySidebar.classList.contains('active')) {
                historySidebar.classList.remove('active');
                if (historyOverlay) {
                    historyOverlay.classList.remove('active');
                }
            }
        });
    }
    
    // 点击历史记录项时的处理
    document.addEventListener('click', async (e) => {
        const historyItem = e.target.closest('.history-item');
        if (historyItem && !e.target.closest('.history-action-btn')) {
            const conversationId = historyItem.dataset.id;
            await continueConversation(conversationId);
        }
    });
    
    // 移动端适配
    if (window.innerWidth <= 768) {
        document.querySelector('.vertical-nav').addEventListener('click', (e) => {
            if (e.target.closest('.nav-item')) {
                document.querySelector('.vertical-nav').classList.remove('expanded');
                document.querySelector('.content-area').style.paddingLeft = '60px';
            }
        });
    }

    // 为主页链接添加点击事件
    const homeLink = document.querySelector('a[href="/"]');
    if (homeLink) {
        homeLink.addEventListener('click', function(e) {
            e.preventDefault();
            createNewConversation();
        });
    }
    
    // 为新建对话按钮添加点击事件
    const newChatBtn = document.querySelector('.new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', function(e) {
            e.preventDefault();
            createNewConversation();
        });
    }

    // 确保导航栏展开按钮正常工作
    const navToggleBtn = document.getElementById('navToggleBtn') || 
                         document.querySelector('.nav-toggle-btn') || 
                         document.querySelector('[data-action="toggle-nav"]');
    
    if (navToggleBtn) {
        // 移除可能存在的旧事件
        const newNavToggleBtn = navToggleBtn.cloneNode(true);
        navToggleBtn.parentNode.replaceChild(newNavToggleBtn, navToggleBtn);
        
        // 添加新的点击事件处理程序
        newNavToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('导航栏展开按钮被点击');
            
            if (typeof window.toggleNavBar === 'function') {
                window.toggleNavBar();
            } else if (window.navManager && typeof window.navManager.toggleNavBar === 'function') {
                window.navManager.toggleNavBar();
            }
        });
    } else {
        console.error('找不到导航栏展开按钮');
    }
}); 

// 初始化用户导航项目
function initUserNavItem() {
    const userNavItem = document.getElementById('user-nav-item');
    if (!userNavItem) return;
    
    // 清除之前可能存在的事件处理器
    const newUserNavItem = userNavItem.cloneNode(true);
    userNavItem.parentNode.replaceChild(newUserNavItem, userNavItem);
    
    const isLoggedIn = !!localStorage.getItem('token');
    const isGuest = localStorage.getItem('guest_mode') === 'true';
    
    // 更新用户导航项目的外观和链接
    if (isLoggedIn && !isGuest) {
        // 已登录用户 - 指向个人资料
        newUserNavItem.setAttribute('href', '/profile');
        const iconEl = newUserNavItem.querySelector('i');
        if (iconEl) {
            iconEl.className = 'fas fa-user-check';
        }
        
        const tooltipEl = newUserNavItem.querySelector('.tooltip');
        if (tooltipEl) {
            tooltipEl.textContent = '个人资料';
        }
        
        // 点击导航到个人资料页面
        newUserNavItem.addEventListener('click', function(e) {
            window.location.href = '/profile';
        });
    } else if (isGuest) {
        // 访客模式 - 提供登录选项
        newUserNavItem.setAttribute('href', 'javascript:void(0);');
        
        const tooltipEl = newUserNavItem.querySelector('.tooltip');
        if (tooltipEl) {
            tooltipEl.textContent = '退出访客模式';
        }
        
        // 点击退出访客模式
        newUserNavItem.addEventListener('click', function(e) {
            e.preventDefault(); // 阻止默认行为
            
            if (confirm('确定要退出访客模式吗？')) {
                console.log("退出访客模式");
                // 移除客户端标记
                localStorage.removeItem('guest_mode');
                
                // 使用fetch请求删除服务器cookie
                fetch('/api/guest/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => {
                    console.log("退出访客响应:", response.status);
                    // 无论响应如何，都跳转到登录页面
                    window.location.href = '/login';
                })
                .catch(error => {
                    console.error("退出访客请求错误:", error);
                    // 即使出错也跳转
                    window.location.href = '/login';
                });
            }
        });
    } else {
        // 未登录 - 指向登录页面
        newUserNavItem.setAttribute('href', '/login');
        
        const tooltipEl = newUserNavItem.querySelector('.tooltip');
        if (tooltipEl) {
            tooltipEl.textContent = '登录/注册';
        }
        
        // 点击导航到登录页面
        newUserNavItem.addEventListener('click', function(e) {
            window.location.href = '/login';
        });
    }
}

// 初始化配置
function initConfig() {
    // 默认开启动态加载模式，提供更流畅的体验
    window.useDynamicLoading = true;
    
    // 如果有其他配置需要初始化，可以在这里添加
    
    // 如果本地存储中有配置，则使用它们
    try {
        const savedConfig = localStorage.getItem('chat_config');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            // 合并配置
            Object.assign(window, config);
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
    
    console.log('功能配置初始化完成:', { 
        useDynamicLoading: window.useDynamicLoading 
    });
}

// 保存配置到本地存储
function saveConfig() {
    try {
        const config = {
            useDynamicLoading: window.useDynamicLoading
        };
        localStorage.setItem('chat_config', JSON.stringify(config));
        console.log('配置已保存');
    } catch (error) {
        console.error('保存配置失败:', error);
    }
}

// 在DOM加载时初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM已加载，初始化功能');
    
    // 初始化配置
    initConfig();
    
    // 初始化用户导航项
    initUserNavItem();
    
    // 添加用户登录跳转处理
    handleUserLogin();
    
    // 添加页面历史记录状态处理
    setupHistoryHandling();
    
    // 初始化导航交互，优先使用类
    try {
        window.navManager = new NavManager();
        console.log('NavManager 初始化成功');
    } catch (error) {
        console.error('NavManager 初始化失败，使用基本功能:', error);
    initNavInteractions();
    }
    
    // 确保历史记录功能正确初始化
    setTimeout(function() {
        initializeHistoryFeature();
    }, 100);
});

// 在页面加载完成后再次检查
window.addEventListener('load', function() {
    console.log("页面完全加载完成，执行最终初始化...");
    
    // 检查对话ID
    checkCurrentPathForConversation();
    
    // 清理所有可能存在的遮罩层
    setTimeout(function() {
        if (typeof window.clearAllOverlays === 'function') {
            window.clearAllOverlays();
        }
    }, 500);
    
    // 系统状态检查和初始化
    checkSystemStatus();
    
    // 再次确保历史按钮功能正确
    resetHistoryButton();
    
    // 初始化导航链接
    initNavLinks();
    
    console.log("最终初始化完成");
});

// 清理所有遮罩层的全局函数
window.clearAllOverlays = function() {
    console.log('执行全局遮罩层清理...');
    
    // 获取所有可能的遮罩层元素
    const overlays = document.querySelectorAll('.overlay, .history-overlay, .modal-backdrop, [class*="overlay"]');
    
    overlays.forEach(overlay => {
        // 移除激活类
        overlay.classList.remove('active', 'show', 'visible');
        
        // 设置内联样式确保不可见
        overlay.style.opacity = '0';
        overlay.style.visibility = 'hidden';
        overlay.style.pointerEvents = 'none';
        
        // 暂时设置display:none以确保不会干扰点击
        setTimeout(() => {
            overlay.style.display = 'none';
            
            // 稍后恢复display以便其他功能可以正常使用它
            setTimeout(() => {
                overlay.style.display = '';
            }, 1000);
        }, 100);
    });
    
    // 同时处理可能的历史侧边栏
    const historySidebar = document.getElementById('history-sidebar');
    if (historySidebar) {
        historySidebar.classList.remove('active');
        historySidebar.style.transform = 'translateX(-100%)';
    }
    
    return '遮罩层清理完成';
};

// 添加键盘快捷键 - Escape 键清理所有遮罩层
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        window.clearAllOverlays();
    }
}); 

// 清除所有历史记录按钮的事件监听，统一使用一个可靠的方法
function resetHistoryButton() {
    console.log("重置历史按钮事件绑定");
    
    // 获取历史按钮元素
    const historyBtn = document.getElementById('nav-history');
    if (!historyBtn) {
        console.error("找不到历史按钮元素!");
        return false;
    }
    
    // 克隆并替换按钮，彻底清除所有事件
    const newHistoryBtn = historyBtn.cloneNode(true);
    historyBtn.parentNode.replaceChild(newHistoryBtn, historyBtn);
    
    // 绑定新的点击事件处理程序
    newHistoryBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log("历史按钮被点击 (resetHistoryButton)");
        
        // 调用全局方法显示历史侧边栏
        toggleHistorySidebar();
    });
    
    return true;
}

// 全局历史侧边栏切换函数
window.toggleHistorySidebar = function() {
    console.log("⚡ 切换历史侧边栏显示状态");
    
    // 获取相关元素
    const historySidebar = document.getElementById('history-sidebar');
    const historyOverlay = document.getElementById('history-overlay');
    
    if (!historySidebar) {
        console.error("❌ 找不到历史侧边栏元素!");
        return;
    }
    
    // 切换侧边栏显示状态
    const isActive = historySidebar.classList.contains('active');
    
    if (isActive) {
        // 当前是激活状态，需要隐藏
        console.log("📊 关闭历史侧边栏");
        historySidebar.classList.remove('active');
        if (historyOverlay) historyOverlay.classList.remove('active');
        
        // 确保没有样式残留
        historySidebar.style.transform = 'translateX(-100%)';
        if (historyOverlay) {
            historyOverlay.style.opacity = '0';
            historyOverlay.style.visibility = 'hidden';
            historyOverlay.style.pointerEvents = 'none';
        }
    } else {
        // 当前是隐藏状态，需要显示
        console.log("📊 打开历史侧边栏");
        historySidebar.classList.add('active');
        if (historyOverlay) {
            historyOverlay.classList.add('active');
            historyOverlay.style.opacity = '1';
            historyOverlay.style.visibility = 'visible';
            historyOverlay.style.pointerEvents = 'auto';
        }
        
        // 清除transform样式
        historySidebar.style.transform = '';
        
        // 根据导航栏状态调整位置
        const verticalNav = document.querySelector('.vertical-nav');
        if (verticalNav && verticalNav.classList.contains('expanded')) {
            historySidebar.style.left = '180px';
        } else {
            historySidebar.style.left = '60px';
        }
        
        // 加载历史记录
        console.log("🔄 准备加载历史记录数据");
        if (window.navManager && typeof window.navManager.loadChatHistory === 'function') {
            console.log("🔄 通过NavManager加载历史记录");
            window.navManager.loadChatHistory();
        } else if (typeof loadChatHistory === 'function') {
            console.log("🔄 通过全局函数加载历史记录");
            loadChatHistory();
        } else {
            console.log("🔄 通过备用方法加载历史记录");
            getChatHistory();
        }
    }
};

// 确保侧边栏可关闭
function setupHistorySidebarClosers() {
    console.log("设置历史侧边栏关闭按钮");
    
    // 获取相关元素
    const historySidebar = document.getElementById('history-sidebar');
    const historyOverlay = document.getElementById('history-overlay');
    const closeBtn = document.querySelector('.history-close');
    
    if (!historySidebar) return;
    
    // 设置关闭按钮事件
    if (closeBtn) {
        // 移除旧事件
        const newCloseBtn = closeBtn.cloneNode(true);
        closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
        
        // 绑定新事件
        newCloseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            window.toggleHistorySidebar();
        });
    }
    
    // 设置遮罩层点击关闭
    if (historyOverlay) {
        // 移除旧事件
        const newOverlay = historyOverlay.cloneNode(true);
        historyOverlay.parentNode.replaceChild(newOverlay, historyOverlay);
        
        // 绑定新事件
        newOverlay.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            window.toggleHistorySidebar();
        });
    }
}

// 增强历史记录功能初始化
function initializeHistoryFeature() {
    // 重置历史按钮
    resetHistoryButton();
    
    // 设置关闭功能
    setupHistorySidebarClosers();
    
    // 设置全局快捷方法
    window.showHistory = function() {
        const historySidebar = document.getElementById('history-sidebar');
        if (historySidebar && !historySidebar.classList.contains('active')) {
            window.toggleHistorySidebar();
        }
    };
    
    window.hideHistory = function() {
        const historySidebar = document.getElementById('history-sidebar');
        if (historySidebar && historySidebar.classList.contains('active')) {
            window.toggleHistorySidebar();
        }
    };
    
    // 通过ESC键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const historySidebar = document.getElementById('history-sidebar');
            if (historySidebar && historySidebar.classList.contains('active')) {
                window.toggleHistorySidebar();
            }
        }
    });
    
    console.log("历史记录功能初始化完成");
}

// 系统状态检查和初始化
function checkSystemStatus() {
    console.log("系统状态检查开始...");
    
    // 检查历史按钮
    const historyBtn = document.getElementById('nav-history');
    if (!historyBtn) {
        console.error("错误: 找不到历史按钮元素! (id='nav-history')");
    } else {
        console.log("✓ 历史按钮存在");
    }
    
    // 检查历史侧边栏
    const historySidebar = document.getElementById('history-sidebar');
    if (!historySidebar) {
        console.error("错误: 找不到历史侧边栏元素! (id='history-sidebar')");
    } else {
        console.log("✓ 历史侧边栏存在");
    }
    
    // 检查遮罩层
    const historyOverlay = document.getElementById('history-overlay');
    if (!historyOverlay) {
        console.error("错误: 找不到历史遮罩层元素! (id='history-overlay')");
        } else {
        console.log("✓ 历史遮罩层存在");
    }
    
    // 重新初始化历史记录功能
    initializeHistoryFeature();
    
    // 检查NavManager状态
    if (!window.navManager) {
        console.error("警告: NavManager未初始化，使用备用功能");
    } else {
        console.log("✓ NavManager已初始化");
    }
    
    console.log("系统状态检查完成");
}

/**
 * 导航管理器类
 * 处理导航相关的所有功能
 */
class NavManager {
    constructor() {
            this.initElements();
            this.initEventListeners();
            
            // 检查URL是否包含对话ID
            window.checkCurrentPathForConversation();
            
            console.log('NavManager 初始化成功');
    }

    initElements() {
        // 获取必要的DOM元素
        this.historyBtn = document.getElementById('nav-history');
        this.historySidebar = document.getElementById('history-sidebar');
        this.historyOverlay = document.getElementById('history-overlay');
        this.historyList = document.getElementById('history-list');
        this.historyCloseBtn = document.querySelector('.history-close');
        
        // 记录初始化状态
        console.log('导航元素初始化状态:', {
            historyBtn: !!this.historyBtn,
            historySidebar: !!this.historySidebar,
            historyList: !!this.historyList
        });
    }

    initEventListeners() {
        // 历史按钮点击事件
        if (this.historyBtn) {
            this.historyBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🔘 历史记录按钮被点击');
                this.toggleHistorySidebar();
            });
        }

        // 关闭按钮点击事件
        if (this.historyCloseBtn) {
            this.historyCloseBtn.addEventListener('click', () => {
                this.closeHistorySidebar();
            });
        }

        // 遮罩层点击关闭
        if (this.historyOverlay) {
            this.historyOverlay.addEventListener('click', () => {
                this.closeHistorySidebar();
            });
        }

        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.historySidebar?.classList.contains('active')) {
                this.closeHistorySidebar();
            }
        });
    }

    // 切换历史记录侧边栏
    toggleHistorySidebar() {
        if (!this.historySidebar) {
            console.error('找不到历史侧边栏元素');
            return;
        }

        const isActive = this.historySidebar.classList.contains('active');
        
        if (isActive) {
            this.closeHistorySidebar();
        } else {
            this.openHistorySidebar();
        }
    }

    // 打开历史记录侧边栏
    openHistorySidebar() {
        console.log('📊 打开历史侧边栏');
        
        // 显示侧边栏
        this.historySidebar.classList.add('active');
        if (this.historyOverlay) {
            this.historyOverlay.classList.add('active');
        }
        
        // 加载历史记录
            this.loadChatHistory();
    }

    // 关闭历史记录侧边栏
    closeHistorySidebar() {
        console.log('📊 关闭历史侧边栏');
        
        this.historySidebar.classList.remove('active');
        if (this.historyOverlay) {
            this.historyOverlay.classList.remove('active');
        }
    }

    // 加载聊天历史记录
    async loadChatHistory() {
        try {
            if (!this.historyList) {
                console.error('找不到历史记录列表元素');
                return;
            }
            
            // 不显示加载动画，直接清空内容
            this.historyList.innerHTML = '';
            
            console.log('📜 历史记录API请求开始 ==================');
            
            // 获取认证信息
            const token = localStorage.getItem('token');
            const userId = localStorage.getItem('user_id');
            
            // 构建请求头
            const headers = {
                'Content-Type': 'application/json'
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            if (userId) {
                headers['X-User-ID'] = userId;
            }

            // 发送API请求
            const url = userId ? `/api/chat/history?user_id=${userId}` : '/api/chat/history';
            console.log('API请求信息:', { url, headers });

            const response = await fetch(url, {
                method: 'GET',
                headers: headers,
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }

            const data = await response.json();
            console.log('历史记录API响应数据:', data);

            if (data.success === true) {
                const historyItems = data.history || data.data || data.conversations || [];
                
                if (Array.isArray(historyItems) && historyItems.length > 0) {
                    console.log(`✅ 获取成功: 找到 ${historyItems.length} 条历史记录`);
                    this.renderChatHistory(historyItems);
                } else {
                    console.log('⚠️ 成功但无数据: 没有找到历史记录');
                    this.showNoHistoryMessage();
                }
            } else {
                throw new Error(data.message || data.error || '未知错误');
            }
        } catch (error) {
            console.error('❌ 历史记录API请求失败:', error);
            this.showErrorMessage(error.message);
        }
    }

    // 渲染聊天历史记录
    renderChatHistory(history) {
        if (!this.historyList) return;

        // 清空现有内容
        this.historyList.innerHTML = '';

        // 创建历史记录列表
        const historyItemsContainer = document.createElement('div');
        historyItemsContainer.className = 'history-items-container';

        history.forEach(item => {
            const historyItem = this.createHistoryItem(item);
            historyItemsContainer.appendChild(historyItem);
        });

        this.historyList.appendChild(historyItemsContainer);
    }

    // 创建单个历史记录项
    createHistoryItem(item) {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.dataset.id = item.id;
            
        const title = item.title || '无标题对话';
        const timestamp = item.updated_at || item.created_at || new Date().toISOString();
        const formattedDate = this.formatDate(timestamp);

        historyItem.innerHTML = `
            <div class="history-item-content">
                <div class="history-title">${this.escapeHtml(title)}</div>
                <div class="history-date">${formattedDate}</div>
            </div>
            <div class="history-actions">
                <button class="history-delete-btn" title="删除">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        // 添加点击事件
        const contentEl = historyItem.querySelector('.history-item-content');
        contentEl.addEventListener('click', () => this.continueConversation(item.id));

        // 添加删除按钮事件
        const deleteBtn = historyItem.querySelector('.history-delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteConversation(item.id);
        });

        return historyItem;
    }

    // 继续对话
    async continueConversation(conversationId) {
        try {
            console.log(`🔄 准备加载对话: ${conversationId}`);
            
            // 关闭历史侧边栏
            this.closeHistorySidebar();
            
            // 开始跳转前记录日志
            console.log(`📜 加载对话API请求开始 ==================`);
            console.log(`请求对话ID: ${conversationId}`);
            console.log(`跳转到: /chat/${conversationId}`);
            
            // 添加到本地存储，便于调试
            localStorage.setItem('last_viewed_conversation', conversationId);
            
            // 跳转到对话页面
            window.location.href = `/chat/${conversationId}`;
        } catch (error) {
            console.error('❌ 继续对话失败:', error);
        }
    }

    // 删除对话
    async deleteConversation(conversationId) {
        if (!confirm('确定要删除这条对话记录吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/chat/conversations/${conversationId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                // 从DOM中移除
                const historyItem = document.querySelector(`.history-item[data-id="${conversationId}"]`);
                if (historyItem) {
                    historyItem.remove();
                }

                // 如果当前正在查看这个对话，跳转回首页
                const currentId = window.location.pathname.match(/\/chat\/(\d+)/);
                if (currentId && currentId[1] === conversationId.toString()) {
                    window.location.href = '/';
                }
            } else {
                throw new Error(data.message || data.error || '删除失败');
            }
        } catch (error) {
            console.error('删除对话失败:', error);
            alert('删除失败: ' + error.message);
        }
    }

    // 显示无历史记录消息
    showNoHistoryMessage() {
        if (!this.historyList) return;
                    this.historyList.innerHTML = `
                        <div class="no-history">
                            <i class="fas fa-history"></i>
                <p>暂无历史对话记录</p>
                <p class="sub-text">开始新对话即可记录在这里</p>
                <div class="error-actions">
                    <button onclick="window.location.href='/'">
                        <i class="fas fa-plus"></i> 新建对话
                    </button>
                </div>
                        </div>
                    `;
                }

    // 显示错误消息
    showErrorMessage(message) {
        if (!this.historyList) return;
        this.historyList.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message || '加载历史记录失败'}</p>
                <div class="error-actions">
                    <button onclick="window.navManager.loadChatHistory()">
                        <i class="fas fa-redo"></i> 重试
                    </button>
                    <button onclick="window.location.href='/'">
                        <i class="fas fa-plus"></i> 新建对话
                    </button>
                </div>
            </div>
        `;
    }

    // 格式化日期
    formatDate(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            }
            
            if (diffDays === 1) {
                return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            }
            
            if (diffDays < 7) {
                const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
                return `${weekdays[date.getDay()]} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            }
            
            if (diffDays < 365) {
                return `${date.getMonth() + 1}月${date.getDate()}日`;
            }
            
            return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
        } catch (e) {
            console.error('日期格式化失败:', e);
            return dateString;
        }
    }

    // HTML转义
    escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// 重新初始化所有导航按钮的链接和事件
function initNavLinks() {
    console.log('初始化导航链接');
    
    // 页面链接映射
    const pageLinks = {
        'nav-home': '/',
        'nav-history': '#', // 特殊处理
        'nav-knowledge': '/knowledge',
        'nav-settings': '/settings',
        'nav-contact': '/contact',
        'nav-user': '/profile'
    };
    
    // 处理每个导航按钮
    document.querySelectorAll('.nav-item').forEach(item => {
        const id = item.id;
        if (!id) return;
        
        // 克隆替换以清除旧事件
        const newItem = item.cloneNode(true);
        item.parentNode.replaceChild(newItem, item);
        
        // 设置正确的href属性
        if (pageLinks[id]) {
            newItem.setAttribute('href', pageLinks[id]);
        }
        
        // 历史按钮特殊处理
        if (id === 'nav-history') {
            newItem.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log("🔘 历史记录按钮被点击 (initNavLinks)");
                if (typeof window.toggleHistorySidebar === 'function') {
                    window.toggleHistorySidebar();
                }
            });
        } 
        // 设置按钮特殊处理
        else if (id === 'nav-settings') {
            newItem.addEventListener('click', function(e) {
                e.preventDefault();
                alert('设置功能即将上线');
            });
        }
        // 首页按钮特殊处理 - 在聊天页面时创建新对话
        else if (id === 'nav-home' && window.location.pathname.startsWith('/chat/')) {
            newItem.addEventListener('click', function(e) {
                e.preventDefault();
                if (typeof window.createNewConversation === 'function') {
                    window.createNewConversation();
                }
            });
        }
        
        console.log(`导航按钮 ${id} 已初始化`);
    });
}

// 添加调试工具
window.debugHistory = function() {
    console.log('==== 历史记录功能诊断 ====');
    
    // 检查用户认证状态
    const token = localStorage.getItem('token');
    const guestMode = localStorage.getItem('guest_mode');
    let userId = localStorage.getItem('user_id');
    
    // 检查cookie中的user_id
    if (!userId) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'user_id') {
                userId = value;
                break;
            }
        }
    }
    
    // 检查session storage
    const sessionUserId = sessionStorage.getItem('user_id');
    
    console.log('认证状态:', {
        'token存在': !!token,
        'token值': token ? `${token.substring(0, 10)}...` : 'null',
        '访客模式': guestMode === 'true',
        '本地存储用户ID': localStorage.getItem('user_id') || '未找到',
        'Cookie用户ID': userId || '未找到',
        'Session存储用户ID': sessionUserId || '未找到'
    });
    
    // 检查历史记录组件
    const historySidebar = document.getElementById('history-sidebar');
    const historyList = document.getElementById('history-list');
    
    console.log('DOM状态:', {
        '历史侧边栏存在': !!historySidebar,
        '历史列表存在': !!historyList,
        '历史侧边栏可见': historySidebar ? historySidebar.classList.contains('active') : false,
        '历史列表内容': historyList ? historyList.innerHTML.substring(0, 100) + '...' : '未找到'
    });
    
    // 尝试直接查询API
    console.log('正在测试API...');
    fetch('/api/chat/history')
        .then(response => {
            console.log('API响应状态:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('API返回数据:', data);
    })
    .catch(error => {
            console.error('API请求失败:', error);
        });
    
    // 显示消息到页面
    const message = `诊断信息已输出到控制台。用户ID: ${userId || '未找到'}, Token: ${token ? '存在' : '不存在'}`;
    if (historyList) {
        const debugInfo = document.createElement('div');
        debugInfo.className = 'debug-info';
        debugInfo.innerHTML = `
            <div class="debug-header">诊断信息</div>
            <div class="debug-item">用户ID: <strong>${userId || '未找到'}</strong></div>
            <div class="debug-item">Token: <strong>${token ? '存在' : '不存在'}</strong></div>
            <div class="debug-item">访客模式: <strong>${guestMode === 'true' ? '是' : '否'}</strong></div>
            <div class="debug-actions">
                <button onclick="localStorage.removeItem('token'); localStorage.removeItem('user_id'); window.location.reload()">
                    清除认证信息
                </button>
                <button onclick="window.location.href='/api/chat/history'">
                    直接访问API
                </button>
            </div>
        `;
        historyList.appendChild(debugInfo);
    }
    
    alert(message);
    return message;
};

// 添加CSS样式
const debugStyle = document.createElement('style');
debugStyle.textContent = `
.debug-info {
    margin-top: 20px;
    padding: 15px;
    background: #f8f9fa;
    border: 1px solid #ddd;
    border-radius: 5px;
}
.debug-header {
    font-weight: bold;
    margin-bottom: 10px;
    color: #dc3545;
}
.debug-item {
    margin-bottom: 5px;
}
.debug-actions {
    margin-top: 10px;
    display: flex;
    gap: 10px;
}
.debug-actions button {
    padding: 5px 10px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
}
`;
document.head.appendChild(debugStyle);

// 添加手动设置用户ID的函数
window.setUserId = function(userId) {
    if (!userId || userId.trim() === '') {
        alert('请输入有效的用户ID');
        return false;
    }

    // 存储用户ID
    localStorage.setItem('user_id', userId);
    
    // 创建一个持久化的cookie，有效期30天
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + 30);
    document.cookie = `user_id=${userId}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
    
    // 保存到会话存储
    sessionStorage.setItem('user_id', userId);
    
    console.log(`已设置用户ID: ${userId}`);
    alert(`已成功设置用户ID: ${userId}\n请刷新页面并尝试打开历史记录`);
    
    return true;
};

// 在历史记录加载失败时，允许手动设置ID
function showManualIdInput() {
    const historyList = document.getElementById('history-list');
    if (!historyList) return;
    
    const inputBox = document.createElement('div');
    inputBox.className = 'manual-id-input';
    inputBox.innerHTML = `
        <div class="input-header">手动设置用户ID</div>
        <div class="input-form">
            <input type="text" id="manual-user-id" placeholder="输入用户ID（数字）">
            <button onclick="window.setUserId(document.getElementById('manual-user-id').value)">
                设置ID
            </button>
        </div>
        <div class="input-help">如果您知道您的用户ID，可以在此手动设置以测试历史记录功能</div>
    `;
    
    historyList.appendChild(inputBox);
}

// 添加相关样式
const manualIdStyle = document.createElement('style');
manualIdStyle.textContent = `
.manual-id-input {
    margin-top: 20px;
    padding: 15px;
    background: #f0f8ff;
    border: 1px solid #b8daff;
    border-radius: 5px;
}
.input-header {
    font-weight: bold;
    margin-bottom: 10px;
    color: #0056b3;
}
.input-form {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
}
.input-form input {
    flex: 1;
    padding: 8px;
    border: 1px solid #ced4da;
    border-radius: 4px;
}
.input-form button {
    padding: 8px 15px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
.input-help {
    font-size: 12px;
    color: #6c757d;
}
`;
document.head.appendChild(manualIdStyle);

// 检查当前URL是否包含对话ID，如果有则加载对话内容
window.checkCurrentPathForConversation = function() {
    const pathMatch = window.location.pathname.match(/\/chat\/(\d+)/);
    if (pathMatch && pathMatch[1]) {
        const conversationId = pathMatch[1];
        console.log(`📄 检测到当前URL包含对话ID: ${conversationId}`);
        
        // 在页面加载完成后加载对话内容
        if (document.readyState === 'complete') {
            loadConversationContent(conversationId);
        } else {
            window.addEventListener('load', () => {
                loadConversationContent(conversationId);
            });
        }
        return true;
    }
    return false;
};

// 加载对话内容
async function loadConversationContent(conversationId) {
    console.log(`📜 加载对话内容API请求开始 ==================`);
    console.log(`对话ID: ${conversationId}`);
    
    // 获取聊天容器
    const chatContainer = document.querySelector('.chat-container') || document.getElementById('chat-messages');
    if (!chatContainer) {
        console.error('❌ 找不到聊天消息容器元素');
        return;
    }
    
    // 显示加载状态
    chatContainer.innerHTML = `
        <div class="loading-message">
            <i class="fas fa-spinner fa-spin"></i> 
            <p>正在加载对话内容...</p>
        </div>
    `;
    
    try {
        // 获取认证信息
        const token = localStorage.getItem('token');
        const userId = localStorage.getItem('user_id');
        
        // 构建请求头
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        if (userId) {
            headers['X-User-ID'] = userId;
        }
        
        console.log('API请求信息:', { 
            url: `/api/chat/conversations/${conversationId}/messages`,
            headers: headers 
        });
        
        // 发送API请求获取对话消息
        const response = await fetch(`/api/chat/conversations/${conversationId}/messages`, {
            method: 'GET',
            headers: headers,
            credentials: 'include'
        });
        
        if (!response.ok) {
            // 如果无法获取消息，尝试获取对话基本信息
            console.log('❌ 无法获取对话消息，尝试获取对话基本信息');
            
            const fallbackResponse = await fetch(`/api/chat/conversations/${conversationId}`, {
                method: 'GET',
                headers: headers,
                credentials: 'include'
            });
            
            if (!fallbackResponse.ok) {
                throw new Error(`服务器错误: ${response.status}`);
            }
            
            const conversationData = await fallbackResponse.json();
            console.log('对话基本信息:', conversationData);
            
            // 使用对话标题和最后回复模拟消息
            const messages = [];
            if (conversationData.conversation) {
                const conv = conversationData.conversation;
                messages.push({
                    role: 'user',
                    content: conv.title || '用户提问',
                    timestamp: conv.created_at
                });
                
                if (conv.last_response) {
                    messages.push({
                        role: 'assistant',
                        content: conv.last_response,
                        timestamp: conv.updated_at
                    });
                }
            }
            
            renderConversationMessages(messages, chatContainer);
            return;
        }
        
        const data = await response.json();
        console.log('对话消息API响应:', data);
        
        if (data.success === true && Array.isArray(data.messages)) {
            console.log(`✅ 获取成功: 找到 ${data.messages.length} 条消息`);
            console.log(`📜 加载对话内容API请求结束 ==================`);
            renderConversationMessages(data.messages, chatContainer);
        } else {
            throw new Error(data.message || data.error || '获取对话消息失败');
        }
    } catch (error) {
        console.error('❌ 加载对话内容失败:', error);
        
        // 显示错误消息
        chatContainer.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                <p>${error.message || '加载对话内容失败'}</p>
                <div class="error-actions">
                    <button onclick="loadConversationContent('${conversationId}')">
                        <i class="fas fa-redo"></i> 重试
                    </button>
                    <button onclick="window.location.href='/'">
                        <i class="fas fa-home"></i> 返回首页
                    </button>
                </div>
            </div>
        `;
    }
}

// 渲染对话消息
function renderConversationMessages(messages, container) {
    if (!messages || !messages.length) {
        container.innerHTML = `
            <div class="no-messages">
                <i class="fas fa-comment-slash"></i>
                <p>没有找到对话消息</p>
                <button onclick="window.location.href='/'">返回首页</button>
            </div>
        `;
        return;
    }
    
    // 清空容器
    container.innerHTML = '';
    console.log(`开始渲染 ${messages.length} 条消息`);
    
    // 渲染每条消息
    messages.forEach((message, index) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`;
        
        // 使用markdown渲染内容（如果有markdown库）
        let content = message.content || '';
        if (window.marked && message.role === 'assistant') {
            try {
                content = window.marked(content);
            } catch (e) {
                console.error('Markdown渲染失败:', e);
            }
        }
        
        // 格式化时间
        let formattedTime = '';
        if (message.timestamp) {
            try {
                const date = new Date(message.timestamp);
                formattedTime = `${date.getFullYear()}-${(date.getMonth()+1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
            } catch (e) {
                console.error('时间格式化失败:', e);
                formattedTime = message.timestamp;
            }
        }
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-role">${message.role === 'user' ? '用户' : 'AI'}</span>
                ${formattedTime ? `<span class="message-time">${formattedTime}</span>` : ''}
            </div>
            <div class="message-content">${content}</div>
        `;
        
        container.appendChild(messageDiv);
    });
    
    console.log(`✅ 成功渲染 ${messages.length} 条消息`);
    
    // 滚动到底部
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
} 