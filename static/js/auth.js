// 认证服务
const AuthService = {
    // 显示错误信息
    showError(message) {
        console.error('认证错误:', message);
        const errorToast = document.createElement('div');
        errorToast.className = 'error-toast';
        errorToast.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(errorToast);
        
        setTimeout(() => {
            errorToast.classList.add('fade-out');
            setTimeout(() => errorToast.remove(), 300);
        }, 3000);
    },

    // 显示成功信息
    showSuccess(message) {
        const errorDiv = document.getElementById('authError');
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        errorDiv.parentNode.insertBefore(successDiv, errorDiv);
        errorDiv.style.display = 'none';
    },

    // 注册
    async register(username, password, email) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, email })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 注册成功后自动登录
                await this.login(username, password);
                return true;
            } else {
                throw new Error(data.error || '注册失败，请稍后重试');
            }
        } catch (error) {
            this.showError(error.message);
            return false;
        }
    },

    // 登录
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('user', JSON.stringify(data.user));
                window.location.href = '/';
                return true;
            } else {
                throw new Error(data.error || '登录失败，请稍后重试');
            }
        } catch (error) {
            this.showError(error.message);
            return false;
        }
    },

    // 获取用户信息
    getUserInfo() {
        try {
            const userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        } catch (e) {
            console.error('解析用户信息失败', e);
            localStorage.removeItem('user');
            return null;
        }
    },

    // 获取用户名
    getUsername() {
        const user = this.getUserInfo();
        return user?.username || '游客';
    },

    // 检查是否登录
    isLoggedIn() {
        try {
            const token = localStorage.getItem('token');
            if (!token) return false;
            
            // 解析token
            const parts = token.split('.');
            if (parts.length !== 3) return false;
            
            const payload = JSON.parse(atob(parts[1]));
            return payload.exp * 1000 > Date.now();
        } catch (e) {
            console.error('验证登录状态失败', e);
            return false;
        }
    },

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/';
    }
};

// 单一入口点，避免重复监听DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // 检查URL参数，看是否是访客模式
    const urlParams = new URLSearchParams(window.location.search);
    const guestMode = urlParams.get('guest_mode');
    
    // 如果是访客模式，设置标志
    if (guestMode === 'true') {
        localStorage.setItem('guest_mode', 'true');
        console.log('已启用访客模式');
    }
    
    // 更新导航栏状态
    updateNavbarState();
    
    // 检查当前URL路径
    const currentPath = window.location.pathname;
    
    // 如果在首页但没有登录，且不是访客模式，则可能需要重定向
    // 由于我们想允许访客访问，需要防止自动重定向到登录页
    if (currentPath === '/' && localStorage.getItem('redirectToLogin') === 'true') {
        localStorage.removeItem('redirectToLogin');
        // 不要自动重定向到登录页
    }
    
    // 绑定登出按钮
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            // 清除所有认证信息
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('guest_mode');
            window.location.href = '/';
        });
    }
    
    // 3. 处理登录表单
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                showErrorMessage('用户名和密码不能为空');
                return;
            }
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    window.location.href = '/';
                } else {
                    // 显示明确的错误消息
                    showErrorMessage(data.error || '登录失败，请稍后重试');
                }
            } catch (error) {
                showErrorMessage('网络错误，请检查您的连接');
                console.error('登录错误:', error);
            }
        });
    }
    
    // 4. 处理注册表单
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('reg-username').value;
            const password = document.getElementById('reg-password').value;
            const email = document.getElementById('reg-email').value;
            
            if (!username || !password) {
                AuthService.showError('用户名和密码不能为空');
                return;
            }
            
            try {
                await AuthService.register(username, password, email);
            } catch (error) {
                AuthService.showError('注册请求失败，请稍后再试');
                console.error('注册错误:', error);
            }
        });
    }
});

// 简化版的导航栏状态更新函数
function updateNavbarState() {
    console.log('更新导航栏状态');
    const token = localStorage.getItem('token');
    const guestMode = localStorage.getItem('guest_mode') === 'true';
    const userInfo = document.querySelector('.user-info');
    const guestActions = document.querySelector('.guest-actions');
    
    if (!userInfo || !guestActions) {
        console.warn('未找到导航栏元素，跳过更新');
        return;
    }
    
    // 简单明确的逻辑：有token显示用户信息，否则显示游客信息
    if (token) {
        userInfo.style.display = 'flex';
        guestActions.style.display = 'none';
        
        // 设置用户名
        const usernameElement = document.querySelector('.username');
        if (usernameElement) {
            try {
                const userJson = localStorage.getItem('user');
                if (userJson) {
                    const user = JSON.parse(userJson);
                    usernameElement.textContent = user.username || '用户';
                }
            } catch (e) {
                console.error('解析用户信息失败:', e);
                usernameElement.textContent = '用户';
            }
        }
    } else {
        userInfo.style.display = 'none';
        guestActions.style.display = 'flex';
    }
}

// 确保错误提示能在页面中显示
function showErrorMessage(message) {
    // 查找错误显示区域
    let errorDiv = document.getElementById('loginError');
    
    // 如果没有找到专门的错误区域，创建一个toast提示
    if (!errorDiv) {
        const errorToast = document.createElement('div');
        errorToast.className = 'error-toast';
        errorToast.innerHTML = `<i class="fas fa-exclamation-circle"></i><span>${message}</span>`;
        document.body.appendChild(errorToast);
        
        setTimeout(() => {
            errorToast.classList.add('fade-out');
            setTimeout(() => errorToast.remove(), 300);
        }, 3000);
    } else {
        // 如果有专门的错误区域，直接显示
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
} 