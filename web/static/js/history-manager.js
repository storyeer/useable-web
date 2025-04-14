/**
 * 历史记录管理器
 * 简化版 - 仅处理历史记录按钮点击和API请求
 */

// 在页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('初始化历史记录管理器...');
    initHistoryButton();
});

/**
 * 初始化历史记录按钮
 */
function initHistoryButton() {
    // 获取历史记录按钮
    const historyBtn = document.getElementById('nav-history');
    
    if (!historyBtn) {
        console.error('❌ 找不到历史记录按钮 (id="nav-history")');
        return;
    }
    
    console.log('✅ 找到历史记录按钮，绑定点击事件');
    
    // 移除可能存在的旧事件监听器
    const newHistoryBtn = historyBtn.cloneNode(true);
    historyBtn.parentNode.replaceChild(newHistoryBtn, historyBtn);
    
    // 为按钮添加点击事件
    newHistoryBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('🔘 历史记录按钮被点击');
        fetchHistoryData();
    });
}

/**
 * 向后端API请求历史记录数据
 */
async function fetchHistoryData() {
    try {
        console.log('📡 开始请求历史记录数据 ===================');
        console.log('请求时间:', new Date().toLocaleString());
        
        // 获取认证信息
        const token = localStorage.getItem('token');
        const userId = localStorage.getItem('user_id') || getUserIdFromCookie();
        
        // 记录认证状态
        console.log('📋 用户认证信息:', {
            'token存在': !!token,
            'token前10位': token ? `${token.substring(0, 10)}...` : 'null',
            '用户ID': userId || '未找到'
        });
        
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
        
        // 构建API URL
        let url = '/api/chat/history';
        if (userId) {
            url += `?user_id=${userId}`;
        }
        
        console.log('📦 API请求详情:', {
            '请求URL': url,
            '请求方法': 'GET',
            '请求头': JSON.stringify(headers, null, 2)
        });
        
        // 发送请求并记录时间
        console.time('API请求耗时');
        
        const response = await fetch(url, {
            method: 'GET',
            headers: headers,
            credentials: 'include' // 包含cookies
        });
        
        console.timeEnd('API请求耗时');
        
        // 记录响应信息
        console.log('📬 API响应状态:', response.status, response.statusText);
        console.log('📬 响应头信息:', Object.fromEntries([...response.headers.entries()]));
        
        // 处理响应
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`服务器错误 (${response.status}): ${errorText}`);
        }
        
        // 解析JSON响应
        const data = await response.json();
        console.log('📄 API响应数据:', data);
        
        // 分析响应结构
        if (data.success === true) {
            const historyItems = data.history || data.data || data.conversations || [];
            console.log(`✅ 成功获取历史记录: ${historyItems.length}条`);
            
            if (Array.isArray(historyItems) && historyItems.length > 0) {
                console.log('📚 历史记录内容示例:', historyItems[0]);
            } else {
                console.log('⚠️ 历史记录为空');
            }
        } else {
            console.warn('⚠️ API返回非成功状态:', data.message || '未知错误');
        }
        
        console.log('📡 历史记录请求完成 ===================');
        return data;
    } catch (error) {
        console.error('❌ 获取历史记录失败:', error);
        console.log('📡 历史记录请求失败 ===================');
        return { success: false, error: error.message };
    }
}

/**
 * 从Cookie中获取用户ID
 */
function getUserIdFromCookie() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'user_id') {
            return value;
        }
    }
    return null;
}

// 导出全局函数，供其他地方调用
window.showHistory = fetchHistoryData; 