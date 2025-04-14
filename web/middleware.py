from functools import wraps
from flask import request, jsonify, redirect, url_for
from user_service import UserService
import jwt
from datetime import datetime
from config import JWT_CONFIG

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 首先检查是否为访客模式
        if request.cookies.get('guest_mode') == 'true' or request.args.get('guest_mode') == 'true':
            print("访客模式已启用，允许访问")
            return f({"is_guest": True, "user_id": -1, "username": "访客"}, *args, **kwargs)
        
        # 获取token
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            token = request.cookies.get('token')
            
        if not token:
            # 如果是API请求，返回401错误
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '未授权访问'}), 401
            
            # 否则重定向到登录页
            return redirect(url_for('login_page'))
        
        try:
            # 验证token
            user_service = UserService()
            user_data = user_service.verify_token(token)
            
            if not user_data:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': '无效的令牌'}), 401
                return redirect(url_for('login_page'))
            
            return f(user_data, *args, **kwargs)
            
        except Exception as e:
            print(f"认证错误: {str(e)}")
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': '认证失败'}), 401
            return redirect(url_for('login_page'))
            
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取token
        token = request.cookies.get('token')
        if not token:
            return jsonify({
                "success": False,
                "error": "未登录",
                "code": "NOT_LOGIN"
            }), 401

        try:
            # 验证token
            user_service = UserService()
            user_data = user_service.verify_token(token)
            
            if not user_data:
                return jsonify({
                    "success": False,
                    "error": "登录已过期",
                    "code": "TOKEN_EXPIRED"
                }), 401

            if user_data.get('role') != 'admin':
                return jsonify({
                    "success": False,
                    "error": "无权限访问",
                    "code": "NO_PERMISSION"
                }), 403

            return f(user_data, *args, **kwargs)
            
        except Exception as e:
            print(f"管理员认证错误: {str(e)}")
            return jsonify({
                "success": False,
                "error": "认证失败",
                "code": "AUTH_ERROR"
            }), 401
            
    return decorated_function 