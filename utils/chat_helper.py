import json
from datetime import datetime
from flask import session

class ChatHelper:
    @staticmethod
    def initialize_session():
        """初始化聊天会话"""
        if 'user_session' not in session:
            session['user_session'] = {
                'chat_history': [],
                'created_at': datetime.now().isoformat(),
                'chat_id': generate_chat_id()
            }
        return session['user_session']
    
    @staticmethod
    def add_message(role, content):
        """添加消息到当前会话"""
        if 'user_session' not in session:
            ChatHelper.initialize_session()
            
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        session['user_session']['chat_history'].append(message)
        session.modified = True
        
        return message
    
    @staticmethod
    def get_chat_history(limit=None):
        """获取聊天历史"""
        if 'user_session' not in session:
            return []
            
        history = session['user_session']['chat_history']
        if limit:
            return history[-limit:]
        return history
    
    @staticmethod
    def clear_history():
        """清除聊天历史"""
        if 'user_session' in session:
            session['user_session']['chat_history'] = []
            session.modified = True

def generate_chat_id():
    """生成唯一会话ID"""
    import uuid
    return str(uuid.uuid4()) 