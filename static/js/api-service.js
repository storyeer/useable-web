/**
 * API服务
 * 处理与服务器的通信
 */
 
// 带认证的fetch函数
async function fetchWithAuth(url, options = {}) {
    try {
        // 简单检查访客模式
        const isGuest = localStorage.getItem('guest_mode') === 'true';
        
        // 设置请求头
        let headers = options.headers || {};
        if (!isGuest && localStorage.getItem('token')) {
            headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
        }
        
        // 设置内容类型
        headers['Content-Type'] = 'application/json';
        
        // 发送请求
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        // 处理401错误
        if (response.status === 401 && !isGuest) {
            // 清理认证信息
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            
            // 除了访客模式外，重定向到登录
            window.location.href = '/login';
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('API请求错误:', error);
        // 显示错误提示
        if (window.SHENJIU && typeof window.SHENJIU.handleError === 'function') {
            window.SHENJIU.handleError('网络请求失败');
        }
        
        // 返回模拟响应
        return {
            ok: false,
            status: 0,
            json: async () => ({success: false, error: '网络连接失败'})
        };
    }
}

// 通用API方法
window.apiService = {
    // 发送聊天消息
    async sendMessage(message) {
        const response = await fetchWithAuth('/api/chat', {
            method: 'POST',
            body: JSON.stringify({message})
        });
        
        if (!response) return null;
        return await response.json();
    },
    
    // 获取聊天历史
    async getHistory() {
        const response = await fetchWithAuth('/api/chat/history');
        if (!response) return null;
        return await response.json();
    }
};

/**
 * 统一的API服务
 * 处理所有与服务器通信的请求
 */
class ApiService {
    /**
     * 获取带认证的请求头
     */
    static getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // 添加token (如果存在)
        const token = localStorage.getItem('token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return headers;
    }
    
    /**
     * 处理响应
     */
    static async handleResponse(response) {
        if (!response.ok) {
            // 处理401未授权错误
            if (response.status === 401) {
                // 除非是访客模式，否则清除凭据并重定向
                if (localStorage.getItem('guest_mode') !== 'true') {
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    window.location.href = '/login';
                }
            }
            
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || '请求失败');
        }
        return await response.json();
    }
    
    /**
     * 发送聊天消息
     */
    static async sendChatMessage(message, conversationId = null) {
        try {
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    message,
                    conversation_id: conversationId
                })
            });
            
            return await this.handleResponse(response);
        } catch (error) {
            console.error('发送消息失败:', error);
            throw error;
        }
    }
    
    /**
     * 获取聊天历史记录
     */
    static async getChatHistory() {
        try {
            const response = await fetch('/api/chat/history', {
                headers: this.getHeaders()
            });
            
            return await this.handleResponse(response);
        } catch (error) {
            console.error('获取历史记录失败:', error);
            throw error;
        }
    }
    
    /**
     * 加载特定对话
     */
    static async loadConversation(conversationId) {
        console.log('ApiService: loadConversation', conversationId);
        try {
            const response = await fetch(`/api/chat/conversations/${conversationId}`);
            return await response.json();
        } catch (error) {
            console.error('加载对话失败:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * 删除对话
     */
    static async deleteConversation(conversationId) {
        console.log('ApiService: deleteConversation', conversationId);
        try {
            // 获取CSRF令牌
            let csrfToken = '';
            
            // 尝试从meta标签获取CSRF令牌
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                csrfToken = metaTag.getAttribute('content');
            }
            
            // 如果meta标签中没有找到，尝试通过API获取
            if (!csrfToken) {
                try {
                    const tokenResponse = await fetch('/get-csrf-token');
                    const tokenData = await tokenResponse.json();
                    csrfToken = tokenData.csrf_token;
                } catch (e) {
                    console.error('获取CSRF令牌失败:', e);
                }
            }
            
            // 准备请求头
            const headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            };
            
            // 添加认证令牌（如果有）
            const authToken = localStorage.getItem('token');
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            const response = await fetch(`/api/chat/conversations/${conversationId}`, {
                method: 'DELETE',
                headers: headers,
                credentials: 'same-origin' // 确保发送cookies
            });
            
            if (!response.ok) {
                // 尝试读取错误详情
                let errorMsg = `删除失败，服务器返回: ${response.status}`;
                try {
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMsg = errorData.error || errorMsg;
                    } else {
                        const text = await response.text();
                        console.error('错误响应内容:', text);
                    }
                } catch (e) {
                    console.error('无法解析错误响应:', e);
                }
                
                return { success: false, error: errorMsg };
            }
            
            return await response.json();
        } catch (error) {
            console.error('删除对话失败:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * 创建新对话
     */
    static async createConversation() {
        try {
            const response = await fetch('/api/chat/conversations', {
                method: 'POST',
                headers: this.getHeaders()
            });
            
            return await this.handleResponse(response);
        } catch (error) {
            console.error('创建对话失败:', error);
            throw error;
        }
    }
    
    /**
     * 用户登录
     */
    static async login(username, password) {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        return await response.json();
    }
    
    /**
     * 用户注册
     */
    static async register(username, password) {
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            return await this.handleResponse(response);
        } catch (error) {
            console.error('注册失败:', error);
            throw error;
        }
    }
    
    /**
     * 用户登出
     */
    static async logout() {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return await response.json();
    }
}

// 将 ApiService 暴露给全局作用域
window.ApiService = ApiService;

// 兼容旧代码的全局API服务
window.apiService = {
    sendMessage: async (message, conversationId) => {
        return await ApiService.sendChatMessage(message, conversationId);
    },
    getHistory: async () => {
        return await ApiService.getChatHistory();
    }
};

/**
 * API服务
 * 处理所有与后端API的交互
 */
window.ApiService = {
    // 获取聊天历史
    getChatHistory: async function() {
        console.log('ApiService: getChatHistory');
        try {
            const response = await fetch('/api/chat/history');
            const data = await response.json();
            console.log('历史数据:', data);
            return data;
        } catch (error) {
            console.error('获取历史记录失败:', error);
            return { success: false, error: error.message };
        }
    },
    
    // 加载对话
    loadConversation: async function(conversationId) {
        console.log('ApiService: loadConversation', conversationId);
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
        console.log('ApiService: deleteConversation', conversationId);
        try {
            const response = await fetch(`/api/chat/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('删除对话失败:', error);
            return { success: false, error: error.message };
        }
    },
    
    // 发送聊天消息
    sendChatMessage: async function(message, conversationId = null) {
        console.log('ApiService: sendChatMessage', {message, conversationId});
        try {
            const formData = new FormData();
            formData.append('message', message);
            if (conversationId) {
                formData.append('conversation_id', conversationId);
            }
            
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                body: formData
            });
            
            return await response.json();
        } catch (error) {
            console.error('发送消息失败:', error);
            return { success: false, error: error.message };
        }
    }
};

console.log('API Service 已加载');

/**
 * 发送消息到服务器并获取响应
 * @param {string} message - 用户消息
 * @param {string|null} conversationId - 会话ID，如果为null则创建新会话
 * @param {boolean} forceNew - 是否强制创建新会话
 * @returns {Promise} - 返回Promise，解析为服务器响应
 */
function sendMessage(message, conversationId = null, forceNew = false) {
    // 获取CSRF令牌
    const csrfToken = getCSRFToken();
    
    return new Promise((resolve, reject) => {
        // 构建请求数据
        const requestData = {
            message: message,
            conversation_id: conversationId,
            force_new: forceNew
        };
        
        // 发送请求
        fetch('/api/chat/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                // 尝试解析错误消息
                return response.json().then(errorData => {
                    throw new Error(errorData.message || '发送消息失败');
                }).catch(e => {
                    // 如果解析JSON失败，使用HTTP状态文本
                    throw new Error(`发送消息失败: ${response.status} ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                resolve({
                    message: data.response,
                    conversationId: data.conversation_id
                });
            } else {
                reject(new Error(data.message || '发送消息失败'));
            }
        })
        .catch(error => {
            console.error('发送消息出错:', error);
            reject(error);
        });
    });
}

/**
 * 获取CSRF令牌
 * 首先尝试从meta标签获取，如果不存在则通过API获取
 */
function getCSRFToken() {
    // 从meta标签获取
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
        return metaTag.getAttribute('content');
    }
    
    // 如果meta标签不存在，通过API获取（同步方式）
    let token = null;
    const xhr = new XMLHttpRequest();
    xhr.open('GET', '/get-csrf-token', false);  // 同步请求
    xhr.onload = function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            token = response.csrf_token;
        }
    };
    xhr.send();
    
    return token;
}

/**
 * 加载特定对话的详细信息
 * @param {string} conversationId - 对话ID
 * @returns {Promise} - 返回Promise，解析为对话详情
 */
function loadConversation(conversationId) {
    // 获取CSRF令牌
    const csrfToken = getCSRFToken();
    
    return new Promise((resolve, reject) => {
        fetch(`/api/chat/conversation/${conversationId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || '加载对话失败');
                }).catch(e => {
                    throw new Error(`加载对话失败: ${response.status} ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // 处理对话数据，将其显示在聊天区域
                const chatArea = document.getElementById('chat-area');
                if (chatArea) {
                    // 清空现有聊天内容
                    chatArea.innerHTML = '';
                    
                    // 设置当前对话ID
                    window.currentConversationId = conversationId;
                    
                    // 更新URL
                    const newUrl = `/chat/${conversationId}`;
                    window.history.pushState({ conversationId }, '', newUrl);
                    
                    // 添加每条消息
                    data.messages.forEach(msg => {
                        // 添加用户消息
                        const userMsg = document.createElement('div');
                        userMsg.className = 'message user-message';
                        userMsg.innerHTML = `
                            <div class="message-content">
                                <p>${escapeHtml(msg.question)}</p>
                            </div>
                        `;
                        chatArea.appendChild(userMsg);
                        
                        // 添加AI回复
                        if (msg.answer) {
                            const aiMsg = document.createElement('div');
                            aiMsg.className = 'message ai-message';
                            aiMsg.innerHTML = `
                                <div class="message-content">
                                    <p>${formatMarkdown(msg.answer)}</p>
                                </div>
                            `;
                            chatArea.appendChild(aiMsg);
                        }
                    });
                    
                    // 滚动到底部
                    chatArea.scrollTop = chatArea.scrollHeight;
                }
                
                resolve(data);
            } else {
                reject(new Error(data.message || '加载对话失败'));
            }
        })
        .catch(error => {
            console.error('加载对话出错:', error);
            reject(error);
        });
    });
}

/**
 * 格式化Markdown文本
 * @param {string} text - Markdown文本
 * @returns {string} - 格式化后的HTML
 */
function formatMarkdown(text) {
    if (!text) return '';
    
    // 如果有Markdown库，使用它来渲染
    if (window.marked) {
        return window.marked(text);
    }
    
    // 简单的Markdown格式化
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // 粗体
        .replace(/\*(.*?)\*/g, '<em>$1</em>')              // 斜体
        .replace(/`(.*?)`/g, '<code>$1</code>')            // 行内代码
        .replace(/\n/g, '<br>');                           // 换行
}

/**
 * HTML转义
 * @param {string} unsafe - 不安全的HTML字符串
 * @returns {string} - 转义后的安全字符串
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}