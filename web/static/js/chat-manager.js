/**
 * 聊天管理器类
 * 处理所有聊天相关的功能
 */
class ChatManager {
    constructor() {
        // 初始化DOM元素
        this.inputElement = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-btn');
        this.thinkButton = document.getElementById('think-btn');
        this.searchButton = document.getElementById('search-btn');
        this.modelSelectButton = document.getElementById('model-select-btn');
        this.modelSelectDropdown = document.getElementById('model-select-dropdown');
        this.messagesContainer = document.getElementById('chat-messages');
        this.titleArea = document.getElementById('title-area');
        this.homeContent = document.getElementById('home-content');
        this.newChatBtn = document.getElementById('new-chat-btn');
        this.newChatWrapper = document.getElementById('new-chat-wrapper');
        
        this.isProcessing = false;
        this.conversationId = null; // 存储当前对话ID
        this.currentModel = '1'; // 存储当前选中的模型，默认为1
        
        // 从URL中获取对话ID
        const pathParts = window.location.pathname.split('/');
        if (pathParts.length > 2 && pathParts[1] === 'chat') {
            this.conversationId = pathParts[2];
            console.log(`从URL加载对话ID: ${this.conversationId}`);
            
            // 如果有对话ID但没有消息，尝试加载对话
            if (this.conversationId && this.messagesContainer && this.messagesContainer.children.length === 0) {
                this.loadConversation(this.conversationId);
            }
        }
        
        // 验证必要的DOM元素
        if (!this.inputElement || !this.sendButton || !this.messagesContainer) {
            console.error('必要的DOM元素未找到:', {
                input: this.inputElement,
                button: this.sendButton,
                messages: this.messagesContainer
            });
            return;
        }
        
        this.initEventListeners();
        this.adjustTextareaHeight(); // 初始化时调整一次高度
    }
    
    // 初始化事件监听器
    initEventListeners() {
        // 发送按钮点击事件
        this.sendButton.addEventListener('click', () => {
            const message = this.inputElement.value.trim();
            if (message) this.sendMessage(message);
        });

        // 思考按钮点击事件
        this.thinkButton.addEventListener('click', () => {
            const message = this.inputElement.value.trim();
            if (message) this.sendMessage(message, 'think');
        });

        // 搜索按钮点击事件
        this.searchButton.addEventListener('click', () => {
            const message = this.inputElement.value.trim();
            if (message) this.sendMessage(message, 'search');
        });

        // 模型选择按钮点击事件
        if (this.modelSelectButton) {
            this.modelSelectButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleModelDropdown();
            });
        }

        // 模型选项点击事件
        if (this.modelSelectDropdown) {
            const options = this.modelSelectDropdown.querySelectorAll('.model-option');
            options.forEach(option => {
                option.addEventListener('click', () => {
                    this.selectModel(option.dataset.model);
                });
            });
        }

        // 点击其他区域关闭下拉框
        document.addEventListener('click', () => {
            if (this.modelSelectDropdown && this.modelSelectDropdown.style.display === 'block') {
                this.modelSelectDropdown.style.display = 'none';
            }
        });

        // 阻止下拉框内部点击事件冒泡
        if (this.modelSelectDropdown) {
            this.modelSelectDropdown.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }

        // 新对话按钮点击事件
        if (this.newChatBtn) {
            this.newChatBtn.addEventListener('click', () => {
                this.startNewChat();
            });
        }

        // 输入框事件
        this.inputElement.addEventListener('input', () => {
            this.sendButton.disabled = !this.inputElement.value.trim();
            this.adjustTextareaHeight();
        });

        // 输入框键盘事件
        this.inputElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !this.sendButton.disabled) {
                e.preventDefault();
                this.sendButton.click();
            }
            // 回车换行时也要调整高度
            if (e.key === 'Enter' && e.shiftKey) {
                setTimeout(() => this.adjustTextareaHeight(), 0);
            }
        });
    }

    // 切换模型选择下拉框显示状态
    toggleModelDropdown() {
        if (this.modelSelectDropdown) {
            this.modelSelectDropdown.style.display = 
                this.modelSelectDropdown.style.display === 'none' ? 'block' : 'none';
        }
    }

    // 选择模型
    selectModel(modelId) {
        if (this.currentModel === modelId) return;
        
        // 更新当前模型
        this.currentModel = modelId;
        
        // 更新UI
        const options = this.modelSelectDropdown.querySelectorAll('.model-option');
        options.forEach(option => {
            if (option.dataset.model === modelId) {
                option.setAttribute('data-selected', 'true');
            } else {
                option.setAttribute('data-selected', 'false');
            }
        });
        
        // 关闭下拉框
        this.modelSelectDropdown.style.display = 'none';
        
        // 显示模型切换提示
        const modelName = this.getModelNameById(modelId);
        this.appendMessage('system', `已切换到模型: ${modelName}`);
    }
    
    // 根据模型ID获取模型名称
    getModelNameById(modelId) {
        const modelMap = {
            '1': 'Qwen2.5-0.5B-Instruct',
            '2': 'DeepSeek-R1-Distill-Qwen-14B'
        };
        return modelMap[modelId] || '未知模型';
    }

    // 调整输入框高度
    adjustTextareaHeight() {
        this.inputElement.style.height = '24px'; // 重置高度为一行
        const scrollHeight = this.inputElement.scrollHeight;
        this.inputElement.style.height = Math.min(scrollHeight, 200) + 'px'; // 限制最大高度
    }

    // 添加消息到界面
    appendMessage(type, content) {
        if (this.messagesContainer.children.length === 0) {
            this.titleArea.style.display = 'none';
            this.homeContent.classList.add('has-messages');
            this.newChatWrapper.style.display = 'block';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        // 根据类型添加不同的头像和样式
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // 对内容进行处理，支持基本的markdown
        if (typeof content === 'string') {
            // 检测内容中的代码块
            if (content.includes('```')) {
                contentDiv.innerHTML = this.formatCodeBlocks(content);
            } else {
                contentDiv.textContent = content;
            }
        } else {
            contentDiv.textContent = String(content);
        }
        
        // 添加时间戳
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        
        // 根据消息类型设置不同的样式
        if (type === 'user') {
            avatarDiv.innerHTML = '<i class="fas fa-user"></i>';
            messageDiv.classList.add('user-message');
        } else if (type === 'assistant') {
            avatarDiv.innerHTML = '<img src="/static/img/robot.svg" alt="AI" onerror="this.src=\'/static/img/robot.png\';">';
            messageDiv.classList.add('bot-message');
        } else if (type === 'error') {
            avatarDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            messageDiv.classList.add('error-message');
        } else if (type === 'system') {
            avatarDiv.innerHTML = '<i class="fas fa-cog"></i>';
            messageDiv.classList.add('system-message');
        }
        
        // 组装消息组件
        contentWrapper.appendChild(contentDiv);
        contentWrapper.appendChild(timestamp);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentWrapper);
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    // 格式化代码块
    formatCodeBlocks(content) {
        // 简单的代码块格式化
        let formatted = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // 将换行符转换为<br>
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }

    // 显示加载动画
    showLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-container';
        loadingDiv.innerHTML = `
            <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        `;
        this.messagesContainer.appendChild(loadingDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        return loadingDiv;
    }

    // 打字机效果
    async typewriterEffect(text, speed = 30) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.innerHTML = '<div class="message-content"></div>';
        this.messagesContainer.appendChild(messageDiv);

        const content = messageDiv.querySelector('.message-content');
        for (let i = 0; i < text.length; i++) {
            content.textContent += text[i];
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }

    // 设置输入状态
    setInputState(disabled) {
        this.inputElement.disabled = disabled;
        this.sendButton.disabled = disabled;
        this.thinkButton.disabled = disabled;
        this.searchButton.disabled = disabled;
        
        if (!disabled) {
            this.inputElement.focus();
        }
    }

    // 启动新对话
    startNewChat() {
        // 清空对话ID
        this.conversationId = null;
        
        // 清空消息区域
        if (this.messagesContainer) {
            this.messagesContainer.innerHTML = '';
        }
        
        // 重置界面
        if (this.titleArea) {
            this.titleArea.style.display = 'flex';
        }
        
        if (this.homeContent) {
            this.homeContent.classList.remove('has-messages');
        }
        
        if (this.newChatWrapper) {
            this.newChatWrapper.style.display = 'none';
        }
        
        // 清空URL中的对话ID
        window.history.pushState({}, '', '/');
    }

    // 加载对话
    async loadConversation(conversationId) {
        try {
            console.log(`加载对话: ${conversationId}`);
            const response = await fetch(`/api/chat/conversations/${conversationId}`);
            const data = await response.json();
            
            if (data.success && data.conversation && data.conversation.messages) {
                // 清空当前消息
                this.messagesContainer.innerHTML = '';
                
                // 显示对话消息
                data.conversation.messages.forEach(msg => {
                    this.appendMessage(msg.role, msg.content);
                });
                
                // 保存对话ID
                this.conversationId = conversationId;
                
                // 更新URL
                window.history.pushState({}, '', `/chat/${conversationId}`);
                
                return true;
                        } else {
                console.error('加载对话失败:', data.error || '未知错误');
                return false;
            }
        } catch (error) {
            console.error('加载对话错误:', error);
            return false;
        }
    }

    // 发送消息
    async sendMessage(message, mode = 'normal') {
        if (this.isProcessing) return;

        try {
            this.isProcessing = true;
            this.setInputState(true);

            // 清空输入框
            this.inputElement.value = '';
            this.adjustTextareaHeight();
            
            // 显示用户消息
            this.appendMessage('user', message);
            
            // 显示加载动画
            const loadingIndicator = this.showLoadingIndicator();

            // 准备请求数据
            const requestData = { 
                message: message,
                mode: mode,
                model: this.currentModel,  // 添加模型选择
                timestamp: new Date().toISOString()
            };
            
            // 如果有对话ID，添加到请求中继续同一个对话
            if (this.conversationId) {
                requestData.conversation_id = this.conversationId;
                console.log(`继续对话: ${this.conversationId}`);
            } else {
                console.log('创建新对话');
            }

            // 发送到后端 API
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify(requestData)
            });

            // 移除加载动画
            loadingIndicator.remove();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // 如果返回了对话ID，存储它
                if (data.conversation_id) {
                    this.conversationId = data.conversation_id;
                    console.log(`对话ID: ${this.conversationId}`);
                    
                    // 更新URL，但不刷新页面
                    window.history.pushState({}, '', `/chat/${this.conversationId}`);
                }
                
                // 显示AI回复，添加打字机效果
                await this.typewriterEffect(data.response);
            } else {
                throw new Error(data.error || '发送失败');
            }

        } catch (error) {
            console.error('Error:', error);
            this.appendMessage('error', '发送失败，请重试');
        } finally {
            this.isProcessing = false;
            this.setInputState(false);
        }
    }
}

// 确保 DOM 完全加载后再初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.chatManager = new ChatManager();
        console.log('ChatManager 初始化成功');
    } catch (error) {
        console.error('ChatManager 初始化失败:', error);
    }
}); 