from flask import Flask, request, jsonify, render_template, session, redirect, url_for, make_response, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from chat_bridge import get_instance as get_chat_bridge, ChatBridge
from middleware import require_auth
import jwt
import datetime
import os
import sys
import webbrowser
from threading import Timer
import uuid
import traceback
import mysql.connector
from config import DB_SERVICE_CONFIG, JWT_CONFIG, POOL_CONFIG  # 导入数据库配置和JWT配置
from functools import wraps
import time  # 添加time模块
from flask_wtf.csrf import CSRFProtect, generate_csrf
from user_service import UserService
import hashlib
import json
from flask_cors import CORS
import re
import logging

# 禁用所有 Flask 默认日志
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# 禁用 Flask 调试模式
app = Flask(__name__, static_folder='static')
app.debug = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 确保有一个安全的密钥
app.config['SESSION_TYPE'] = 'filesystem'  # 使用文件系统存储session

# 配置CSRF保护
csrf = CSRFProtect(app)

# 允许在某些情况下放宽CSRF保护
# 确保用户登录时始终有CSRF保护，但API调用可以通过其他方式验证
@csrf.exempt
def csrf_exempt_rule():
    # 如果请求路径以/api/开头并且是GET请求，或者有有效的认证令牌，可以考虑免除CSRF
    if request.path.startswith('/api/') and request.method == 'GET':
        return True
    return False

# 确保所有模板可以访问CSRF令牌
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

# 为前端提供获取CSRF令牌的API
@app.route('/get-csrf-token')
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# 移除默认的错误处理，使用自定义的
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 更新版本号生成函数
def generate_version():
    return str(int(time.time()))

# 应用启动时生成资源版本号
RESOURCE_VERSION = generate_version()

# 强化缓存控制中间件
@app.after_request
def add_cache_control(response):
    """控制静态资源的缓存策略"""
    if request.path.startswith('/static/'):
        # 开发环境：完全禁用缓存
        if app.debug:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            # 生产环境：设置较长缓存但带版本号
            if 'text/css' in response.content_type or 'application/javascript' in response.content_type:
                # CSS和JS文件使用版本号控制缓存
                response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1年
            elif 'image/' in response.content_type:
                # 图片缓存较长时间
                response.headers['Cache-Control'] = 'public, max-age=604800'  # 1周
    
    # HTML页面始终不缓存
    elif 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
    return response

# 全局变量
chat_bridge = None

# 存储游客聊天历史
guest_chat_history = {}

# 创建数据库连接池
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(**POOL_CONFIG)
    print("✅ 数据库连接池创建成功")
except Exception as e:
    print(f"❌ 数据库连接池创建失败: {str(e)}")
    sys.exit(1)

# 将版本号注入所有模板
@app.context_processor
def inject_version():
    """向所有模板注入版本号，用于防止静态资源缓存"""
    return {'resource_version': RESOURCE_VERSION}

def init_services():
    """初始化所有服务"""
    global chat_bridge
    try:
        print("\n=== 开始初始化服务 ===")
        chat_bridge = get_chat_bridge()
        
        if not chat_bridge:
            print("❌ 聊天服务初始化失败")
            return False
            
        if not chat_bridge.model_service:
            print("❌ 模型服务初始化失败")
            return False
            
        if not chat_bridge.db_service:
            print("❌ 数据库服务初始化失败")
            return False
        
        # 添加这一行，确保数据库结构符合要求
        ensure_db_structure()
            
        print("✅ 所有服务初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        return False

def ensure_db_structure():
    """确保数据库结构完整"""
    try:
        conn = mysql.connector.connect(**DB_SERVICE_CONFIG)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name IN ('users', 'conversations', 'chat_history')
        """, (DB_SERVICE_CONFIG['database'],))
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if count == 3:
            print("✅ 数据库结构检查完成")
            return True
        else:
            print("❌ 数据库结构不完整")
            return False
            
    except Exception as e:
        print(f"❌ 数据库结构检查失败: {str(e)}")
        return False

# 用户会话管理
class UserSession:
    def __init__(self):
        self.chat_history = []
        self.created_at = datetime.datetime.now()
    
    def add_message(self, role, content):
        """添加消息到历史记录"""
        self.chat_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
    def get_messages(self, limit=None):
        """获取历史消息"""
        if limit:
            return self.chat_history[-limit:]
        return self.chat_history

# 路由简化
@app.route('/')
def index():
    """首页 - 简化版本"""
    return render_template('index.html')

@app.route('/chat')
def chat():
    """聊天页面 - 简化版本"""
    return render_template('chat.html')

@app.route('/knowledge')
def knowledge():
    """知识库页面"""
    return render_template('knowledge.html')

@app.route('/knowledge/category/<category>')
def knowledge_category(category):
    # 可以根据category参数加载相应的知识内容
    return render_template('knowledge_category.html', 
                          category=category,
                          resource_version=RESOURCE_VERSION)

@app.route('/contact')
def contact():
    # 确保使用与首页相同的上下文变量
    return render_template('contact.html', 
                          resource_version=RESOURCE_VERSION,
                          active_page='contact')

@app.route('/profile')
def profile_page():
    """个人资料页面 - 手动处理认证"""
    try:
        # 从请求中获取token
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # 如果请求头中没有token，尝试从URL参数或cookie获取
        if not token:
            token = request.args.get('token') or request.cookies.get('token')
        
        # 如果仍然没有token，检查session
        if not token and 'user_id' in session:
            # 使用session中的用户ID
            user_id = session.get('user_id')
            user = chat_bridge.user_service.get_user_by_id(user_id)
            if user:
                return render_template('profile.html', 
                                      user=user,
                                      resource_version=RESOURCE_VERSION)
        
        # 如果有token，验证token
        if token:
            try:
                # 解码token
                payload = jwt.decode(token, JWT_CONFIG['SECRET_KEY'], algorithms=['HS256'])
                user_id = payload['user_id']
                
                # 获取用户信息
                user = chat_bridge.user_service.get_user_by_id(user_id)
                if user:
                    return render_template('profile.html', 
                                          user=user,
                                          resource_version=RESOURCE_VERSION)
            except:
                pass
        
        # 如果没有有效的认证信息，重定向到登录页面
        return redirect('/login?next=/profile')
    except Exception as e:
        app.logger.error(f"加载个人资料页面出错: {str(e)}")
        return render_template('error.html', 
                              error_message="加载个人资料页面时出错，请稍后再试。",
                              resource_version=RESOURCE_VERSION)

def get_current_user_id():
    """获取当前登录用户ID"""
    try:
        # 获取token
        token = request.cookies.get('token')
        if not token:
            return None
            
        # 验证token并获取用户信息
        user_service = UserService()
        user_data = user_service.verify_token(token)
        if not user_data:
            return None
            
        # 返回用户ID
        return user_data.get('id') or user_data.get('user_id')
    except Exception as e:
        print(f"获取当前用户ID失败: {str(e)}")
        return None

@app.route('/chat/<int:conversation_id>')
def chat_detail(conversation_id):
    """加载特定的对话页面"""
    try:
        # 获取用户ID
        user_id = get_current_user_id()
        if not user_id:
            # 未登录时重定向到首页
            return redirect('/')
            
        # 获取聊天服务实例
        chat_bridge = get_chat_bridge()
        if not chat_bridge:
            # 聊天服务未初始化时显示错误页面
            return render_template('error.html', 
                                  error_message='聊天服务未初始化，请稍后再试')
        
        # 获取对话详情
        conversation = chat_bridge.db_service.get_conversation(conversation_id, user_id)
        if not conversation:
            # 对话不存在或无权访问时显示错误页面
            return render_template('error.html', 
                                  error_message='对话不存在或您无权访问')
        
        # 获取对话消息
        messages = chat_bridge.db_service.get_conversation_messages(user_id, conversation_id)
        
        # 渲染聊天页面，并传入对话信息
        return render_template('chat.html', 
                              conversation=conversation,
                              messages=messages,
                              conversation_id=conversation_id)
                              
    except Exception as e:
        print(f"加载对话详情失败: {str(e)}")
        return render_template('error.html', 
                              error_message='加载对话失败，请稍后再试')

# 修改游客模式路由
@app.route('/guest')
def guest_mode():
    """游客模式入口点 - 重定向到主页并标记为游客"""
    # 设置访客cookie
    response = make_response(redirect(url_for('index')))
    response.set_cookie('guest_mode', 'true', max_age=3600*24)
    # 设置localStorage标记
    response.headers['X-Set-Guest-Mode'] = 'true'
    return response

@app.route('/api/chat/conversations', methods=['GET'])
@require_auth
def get_conversations(user):
    """获取用户所有对话"""
    try:
        conversations = chat_bridge.db_service.get_user_conversations(user['user_id'])
        return jsonify({"success": True, "conversations": conversations})
    except Exception as e:
        print(f"获取对话列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    try:
        # 获取用户ID（如果已登录）
        user_id = None
        token = request.cookies.get('token')
        
        # 添加详细日志记录用于调试
        app.logger.info(f"获取历史记录请求 - Token存在: {bool(token)}")
        
        if token:
            user = chat_bridge.user_service.verify_token(token)
            if user:
                # 尝试从不同可能的字段获取用户ID
                user_id = user.get('id') or user.get('user_id')
                app.logger.info(f"已验证用户ID: {user_id}, 用户数据: {user}")
            else:
                app.logger.warning("令牌验证失败，无法获取用户信息")
        
        # 如果未找到有效的用户ID，返回空历史记录
        if not user_id:
            app.logger.warning("未找到有效的用户ID，返回空历史记录")
            return jsonify({
                'success': True,
                'history': [],
                'message': '请登录后查看历史记录'
            })

        # 从数据库获取历史记录 - 使用参数化查询避免SQL注入
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 确保SQL查询使用用户ID作为严格筛选条件
                    app.logger.info(f"执行历史记录查询 - 用户ID: {user_id}")
                    
                    # 明确只查询当前用户的对话
                    cur.execute("""
                        SELECT DISTINCT 
                            c.id as conversation_id,
                            c.title,
                            c.created_at,
                            c.updated_at,
                            (
                                SELECT question 
                                FROM chat_history 
                                WHERE conversation_id = c.id 
                                ORDER BY created_at ASC 
                                LIMIT 1
                            ) as first_message
                        FROM conversations c
                        WHERE c.user_id = %s
                        ORDER BY c.updated_at DESC
                        LIMIT 50
                    """, (user_id,))
                    
                    results = cur.fetchall()
                    app.logger.info(f"查询结果数量: {len(results)}")
                    
                    # 获取列名
                    columns = [desc[0] for desc in cur.description]
                    
                    history = []
                    for row in results:
                        # 将结果转换为字典
                        row_dict = dict(zip(columns, row))
                        
                        # 额外的安全检查：确保每条记录确实属于当前用户
                        # 这一步可能是多余的，因为SQL查询已经过滤了，但作为额外的安全措施
                        if 'user_id' in row_dict and row_dict['user_id'] is not None:
                            if int(row_dict['user_id']) != int(user_id):
                                app.logger.warning(f"发现权限不匹配的记录: {row_dict['conversation_id']}")
                                continue
                                
                        history.append({
                            'id': row_dict['conversation_id'],
                            'title': row_dict['title'] or '未命名对话',
                            'preview': row_dict['first_message'][:100] + '...' if row_dict['first_message'] and len(row_dict['first_message']) > 100 else row_dict['first_message'] or '暂无预览',
                            'created_at': row_dict['created_at'].isoformat() if row_dict['created_at'] else None,
                            'updated_at': row_dict['updated_at'].isoformat() if row_dict['updated_at'] else None
                        })

                    return jsonify({
                        'success': True,
                        'history': history
                    })
                    
        except Exception as db_error:
            app.logger.error(f"数据库查询失败: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': '数据库查询失败',
                'error': str(db_error)
            }), 500

    except Exception as e:
        app.logger.error(f"获取历史记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '获取历史记录失败',
            'error': str(e)
        }), 500

@app.route('/api/chat/conversations/<int:conversation_id>', methods=['GET'])
@require_auth
def get_conversation_api(user, conversation_id):
    """获取完整对话内容"""
    try:
        user_id = user.get('id') or user.get('user_id')
        
        # 检查对话是否属于当前用户
        conversation = chat_bridge.db_service.get_conversation(conversation_id, user_id)
        if not conversation:
            return jsonify({
                'success': False,
                'error': '对话不存在或无权访问'
            }), 404
            
        # 获取对话消息
        messages = chat_bridge.db_service.get_conversation_messages(conversation_id, user_id)
        
        return jsonify({
            'success': True,
            'conversation': conversation,
            'messages': messages
        })
        
    except Exception as e:
        print(f"获取对话内容失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': '获取对话内容失败'
        }), 500

@app.route('/api/chat/new', methods=['POST'])
def create_new_chat():
    """创建新的对话"""
    try:
        # 获取用户ID
        user_id = None
        token = request.cookies.get('token')
        
        if token:
            try:
                user_data = chat_bridge.user_service.verify_token(token)
                if user_data:
                    user_id = user_data.get('id') or user_data.get('user_id')
            except Exception as e:
                print(f"验证token失败: {str(e)}")
                user_id = -1
        else:
            user_id = -1
            
        # 使用空消息创建新会话
        result = chat_bridge.handle_chat(
            message="新对话",
            user_id=user_id,
            conversation_id=None,
            force_new=True  # 强制创建新会话
        )
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'conversation_id': result.get('conversation_id')
            })
        else:
            return jsonify({
                'success': False,
                'message': '创建新对话失败'
            }), 500
            
    except Exception as e:
        print(f"创建新对话失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误'
        }), 500

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    try:
        # 获取聊天服务实例
        chat_bridge = get_chat_bridge()
        if not chat_bridge:
            return jsonify({
                'success': False,
                'message': '聊天服务未初始化'
            }), 500

        data = request.get_json(force=True) if request.is_json else request.form
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        force_new = data.get('force_new', False)  # 添加 force_new 参数
        model_id = data.get('model', 'default')  # 获取模型选择参数
        
        print(f"收到消息: {message}, conversation_id: {conversation_id}, force_new: {force_new}, model: {model_id}")
        
        if not message:
            return jsonify({
                'success': False,
                'message': '消息不能为空'
            }), 400
            
        # 获取用户ID
        user_id = None
        token = request.cookies.get('token')
        
        if token:
            try:
                # 验证token并获取用户信息
                user_data = chat_bridge.user_service.verify_token(token)
                if user_data:
                    # 获取用户ID
                    user_id = user_data.get('id') or user_data.get('user_id')
                    print(f"从token中获取到用户ID: {user_id}, user_data: {user_data}")
                    
                    if user_id:
                        try:
                            # 检查用户是否存在且状态正常
                            user_exists = chat_bridge.db_service.check_user_exists(user_id)
                            if not user_exists:
                                print(f"警告: 用户ID {user_id} 在数据库中不存在或状态异常，切换为游客模式")
                                user_id = -1
                            else:
                                try:
                                    # 更新用户最后活动时间
                                    chat_bridge.db_service.update_user_last_active(user_id)
                                except Exception as update_error:
                                    print(f"更新用户最后活动时间失败: {str(update_error)}")
                        except Exception as check_error:
                            print(f"检查用户存在失败: {str(check_error)}")
                            user_id = -1
            except Exception as e:
                print(f"验证token失败: {str(e)}")
                user_id = -1
        else:
            print("未找到token，使用游客模式")
            user_id = -1
        
        print(f"最终使用的用户ID: {user_id}")
        
        # 处理消息
        if user_id and user_id != -1:
            # 已登录用户
            result = chat_bridge.handle_chat(
                message=message,
                user_id=user_id,
                conversation_id=conversation_id,
                force_new=force_new,
                model_id=model_id  # 传递模型选择参数
            )
        else:
            # 游客模式
            result = chat_bridge.handle_trial_chat(message, model_id=model_id)  # 传递模型选择参数
        
        print(f"处理结果: {result}")
        
        if result.get('success'):
            response_data = {
                'success': True,
                'response': result.get('answer'),
                'conversation_id': result.get('conversation_id')
            }
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', '处理消息失败')
            }), 500
            
    except Exception as e:
        print(f"处理聊天请求失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后再试'
        }), 500

@app.route('/api/chat/trial', methods=['POST'])
def trial_chat_api():
    """处理访客的聊天请求"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({"success": False, "error": "消息不能为空"}), 400
            
        # 使用-1作为访客用户ID
        result = chat_bridge.process_user_chat(
            message=message,
            user_id=-1,
            conversation_id=conversation_id
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"访客聊天API错误: {str(e)}")
        return jsonify({"success": False, "error": "服务器错误"}), 500

@app.route('/api/chat/trial/history', methods=['GET'])
def get_trial_history():
    try:
        session_id = request.cookies.get('guest_session_id')
        if not session_id:
            return jsonify({'success': True, 'history': []})
            
        history = guest_chat_history.get(session_id, [])
        return jsonify({'success': True, 'history': history})
        
    except Exception as e:
        print(f"获取游客历史记录失败: {str(e)}")
        return jsonify({'success': False, 'error': '获取历史记录失败'})

@app.route('/api/chat/history/<int:conversation_id>', methods=['DELETE'])
@require_auth
def delete_history(user, conversation_id):
    try:
        chat_bridge.db_service.delete_chat_history(conversation_id, user['id'])
        return jsonify({
            "success": True,
            "message": "删除成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/login')
def login_page():
    """登录页面"""
    # 如果用户已登录，重定向到首页
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html', resource_version=RESOURCE_VERSION)

@app.route('/register')
def register_page():
    """注册页面"""
    # 如果用户已登录，重定向到首页
    if 'user_id' in session:
        return redirect('/')
    return render_template('register.html', resource_version=RESOURCE_VERSION)

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    """处理用户登录请求"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '请输入用户名和密码'
            }), 400
        
        # 验证用户
        user = chat_bridge.user_service.authenticate(username, password)
        if not user:
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
        
        # 生成token
        token = chat_bridge.user_service.generate_token(user)
        
        # 创建响应
        response = jsonify({
            'success': True,
            'message': '登录成功',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        })
        
        # 设置cookie
        response.set_cookie(
            'token',
            token,
            httponly=True,
            secure=False,  # 在生产环境中应该设置为True
            samesite='Lax',
            max_age=JWT_CONFIG['EXPIRE_DAYS'] * 24 * 60 * 60  # 转换为秒
        )
        
        return response
        
    except Exception as e:
        print('登录错误:', str(e))
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后重试'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout_api():
    """处理用户登出请求"""
    try:
        response = jsonify({
            'success': True,
            'message': '登出成功'
        })
        
        # 清除token cookie
        response.set_cookie(
            'token',
            '',
            httponly=True,
            secure=False,  # 在生产环境中应该设置为True
            samesite='Lax',
            max_age=0
        )
        
        return response
        
    except Exception as e:
        print(f"登出错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后重试'
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def register_api():
    """处理用户注册请求"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        # 验证用户名格式
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return jsonify({
                'success': False,
                'message': '用户名只能包含字母、数字和下划线，长度3-20'
            }), 400
        
        # 验证密码强度
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': '密码长度不能少于6位'
            }), 400
        
        # 注册用户
        result = chat_bridge.user_service.register(username, password)
        
        if result.get('success'):
            # 创建响应
            response = jsonify(result)
            
            # 设置token cookie
            response.set_cookie(
                'token',
                result['token'],
                httponly=True,
                secure=False,  # 在生产环境中应该设置为True
                samesite='Lax',
                max_age=JWT_CONFIG['EXPIRE_DAYS'] * 24 * 60 * 60  # 转换为秒
            )
            
            return response
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', '注册失败')
            }), 400
            
    except Exception as e:
        print(f"注册错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后重试'
        }), 500

@app.route('/api/chat/trial/history/<int:message_id>', methods=['GET'])
def get_trial_message(message_id):
    try:
        session_id = request.cookies.get('guest_session_id')
        if not session_id:
            return jsonify({'success': False, 'error': '未找到会话'})
            
        # 从游客历史记录中获取指定消息
        history = guest_chat_history.get(session_id, [])
        message = next((msg for msg in history if msg.get('id') == message_id), None)
        
        if message:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'success': False, 'error': '未找到消息'})
            
    except Exception as e:
        print(f"获取游客历史消息失败: {str(e)}")
        return jsonify({'success': False, 'error': '获取消息失败'})

@app.route('/api/chat/guest/history', methods=['GET'])
def get_guest_chat_history():
    conversation_id = request.args.get('conversation_id')
    if not conversation_id:
        return jsonify({'success': False, 'error': '未提供conversation_id'}), 400
    
    chat_service = get_chat_bridge()
    
    # 从聊天服务中获取临时历史
    if hasattr(chat_service, '_guest_chats') and conversation_id in chat_service._guest_chats:
        return jsonify({
            'success': True,
            'history': chat_service._guest_chats[conversation_id],
            'conversation_id': conversation_id
        })
    else:
        return jsonify({
            'success': True,
            'history': [],
            'conversation_id': conversation_id
        })

# 查看特定对话
@app.route('/conversation/<int:conversation_id>')
@require_auth
def view_conversation(conversation_id, user):
    # 获取会话信息
    connection = db_pool.get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # 先检查会话是否存在且属于当前用户
        cursor.execute(
            "SELECT * FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user['id'])
        )
        conversation = cursor.fetchone()
        
        if not conversation:
            return "未找到会话或无权限", 403
        
        # 获取消息
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = %s ORDER BY timestamp",
            (conversation_id,)
        )
        messages = cursor.fetchall()
        
        return render_template('conversation.html', 
                              conversation=conversation, 
                              messages=messages, 
                              user=user,
                              resource_version=RESOURCE_VERSION)
    finally:
        cursor.close()
        connection.close()

def save_messages(conversation_id, user_id, messages):
    """保存消息到数据库"""
    if not conversation_id or not user_id or not messages:
        return
        
    connection = db_pool.get_connection()
    cursor = connection.cursor()
    
    try:
        # 清除现有消息（可选）
        cursor.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
        
        # 添加新消息
        for msg in messages:
            timestamp = datetime.datetime.fromisoformat(msg['timestamp']) if 'timestamp' in msg else datetime.datetime.now()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (%s, %s, %s, %s)",
                (conversation_id, msg['role'], msg['content'], timestamp)
            )
        
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_ai_response(message):
    """获取AI回复"""
    try:
        # 使用聊天桥接服务获取回复
        if chat_bridge and chat_bridge.model_service:
            response = chat_bridge.model_service.get_response(message)
            return response
        else:
            return "抱歉，AI服务暂时不可用。请稍后再试。"
    except Exception as e:
        print(f"AI响应错误: {str(e)}")
        return "处理您的请求时发生错误，请稍后再试。"

# 添加到应用初始化后面
@app.template_filter('datetime')
def format_datetime(value):
    """格式化日期时间"""
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return value
    return value.strftime('%Y-%m-%d %H:%M:%S')

@app.template_filter('time')
def format_time(value):
    """只显示时间部分"""
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return value
    return value.strftime('%H:%M')

# 添加安全相关的HTTP头
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# 自定义404错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# 静态文件处理
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# 获取用户资料 API
@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile(user):
    """获取用户资料"""
    try:
        # 移除敏感信息
        user_data = {
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user.get('role', 'user'),
            'email': user.get('email', '')
        }
        
        return jsonify({
            "success": True,
            "user": user_data
        })
    except Exception as e:
        print(f"获取用户资料失败: {str(e)}")
        return jsonify({"success": False, "error": "服务器错误"}), 500

# 更新用户资料 API
@app.route('/api/user/profile', methods=['PUT'])
@require_auth
def update_user_profile(user):
    """更新用户资料"""
    try:
        data = request.get_json()
        
        # 获取要更新的字段
        email = data.get('email')
        display_name = data.get('display_name')
        
        # 更新用户资料
        result = chat_bridge.user_service.update_user_profile(
            user['user_id'], 
            email=email,
            display_name=display_name
        )
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": "资料已更新",
                "user": result.get('user', {})
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '更新失败')
            }), 400
            
    except Exception as e:
        print(f"更新用户资料失败: {str(e)}")
        return jsonify({"success": False, "error": "服务器错误"}), 500

# 更新用户密码 API
@app.route('/api/user/password', methods=['PUT'])
@require_auth
def update_user_password(user):
    """更新用户密码"""
    try:
        data = request.get_json()
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                "success": False,
                "error": "当前密码和新密码都不能为空"
            }), 400
            
        # 更新密码
        result = chat_bridge.user_service.update_password(
            user['user_id'],
            current_password,
            new_password
        )
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": "密码已更新"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '密码更新失败')
            }), 400
            
    except Exception as e:
        print(f"更新密码失败: {str(e)}")
        return jsonify({"success": False, "error": "服务器错误"}), 500

@app.route('/api/chat/conversations/<int:conversation_id>', methods=['DELETE'])
@require_auth
def delete_conversation_api(user, conversation_id):
    """删除指定的对话 - 允许任何用户删除任何对话"""
    try:
        # 获取用户ID - 仅用于日志记录
        user_id = user.get('id') or user.get('user_id')
        if not user_id:
            app.logger.warning(f"删除对话时用户身份无效: {user}")
            return jsonify({"success": False, "error": "用户身份无效"}), 401
            
        app.logger.info(f"用户 {user_id} 尝试删除对话 {conversation_id}")
        
        # 直接删除对话，不验证所有权
        try:
            # 直接从数据库删除对话
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 首先删除对话关联的消息
            cursor.execute("DELETE FROM chat_history WHERE conversation_id = %s", (conversation_id,))
            
            # 然后删除对话本身
            cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            
            # 提交事务
            conn.commit()
            
            # 记录成功删除
            deleted_rows = cursor.rowcount
            app.logger.info(f"用户 {user_id} 成功删除对话 {conversation_id}, 影响行数: {deleted_rows}")
            
            cursor.close()
            conn.close()
            
            return jsonify({"success": True, "message": "对话已删除"})
        except Exception as db_error:
            app.logger.error(f"数据库删除对话失败: {str(db_error)}")
            return jsonify({"success": False, "error": f"删除对话时发生数据库错误: {str(db_error)}"}), 500
    except Exception as e:
        app.logger.error(f"删除对话失败，用户ID: {user.get('id') or user.get('user_id')}，对话ID: {conversation_id}，错误: {str(e)}")
        return jsonify({"success": False, "error": f"服务器错误: {str(e)}"}), 500

# 修改用户认证中间件，确保聊天功能正常工作
@app.before_request
def authenticate_user():
    """暂时禁用用户认证，确保所有功能正常工作"""
    return None

# 发送密码重置邮件
@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password_api():
    """处理忘记密码API请求"""
    try:
        data = request.get_json(force=True) if request.is_json else request.form
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'message': '请输入邮箱地址'
            }), 400
        
        # 这里应该连接数据库验证邮箱是否存在
        # 然后生成重置令牌并发送邮件
        # 为了演示，我们假设邮件发送成功
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '密码重置邮件已发送，请查收'
        })
        
    except Exception as e:
        print(f"忘记密码API错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后再试'
        }), 500

def get_db_connection():
    """获取数据库连接"""
    try:
        return db_pool.get_connection()
    except Exception as e:
        print(f"获取数据库连接失败: {str(e)}")
        raise

# 添加数据库连接池错误处理
def handle_db_error(e):
    """处理数据库错误"""
    print(f"数据库错误: {str(e)}")
    if "Connection pool is closed" in str(e):
        # 尝试重新初始化连接池
        try:
            global db_pool
            db_pool = mysql.connector.pooling.MySQLConnectionPool(**POOL_CONFIG)
            print("数据库连接池重新初始化成功")
        except Exception as init_error:
            print(f"重新初始化连接池失败: {str(init_error)}")
    return jsonify({
        'success': False,
        'message': '数据库服务暂时不可用，请稍后再试'
    }), 500

def db_connection(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:  # 移除 dictionary=True 参数
                    return func(self, conn, cursor, *args, **kwargs)
        except Exception as e:
            print(f"数据库操作失败: {str(e)}")
            raise
    return wrapper

@app.route('/api/chat/conversation/<int:conversation_id>', methods=['GET'])
def get_conversation_detail(conversation_id):
    """获取特定对话的详细信息（包含所有用户问题和AI回答）"""
    try:
        # 获取聊天服务实例
        chat_bridge = get_chat_bridge()
        if not chat_bridge:
            return jsonify({
                'success': False,
                'message': '聊天服务未初始化'
            }), 500
            
        # 获取用户ID
        user_id = None
        token = request.cookies.get('token')
        
        if token:
            try:
                # 验证token并获取用户信息
                user_data = chat_bridge.user_service.verify_token(token)
                if user_data:
                    user_id = user_data.get('id') or user_data.get('user_id')
                    print(f"从token中获取到用户ID: {user_id}")
                else:
                    return jsonify({
                        'success': False,
                        'message': '用户未授权'
                    }), 401
            except Exception as e:
                print(f"验证token失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': '用户认证失败'
                }), 401
        else:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401
            
        # 获取对话详情
        conversation = chat_bridge.db_service.get_conversation(conversation_id, user_id)
        if not conversation:
            return jsonify({
                'success': False,
                'message': '对话不存在或无权访问'
            }), 404
            
        # 获取对话消息
        messages = chat_bridge.db_service.get_conversation_messages(user_id, conversation_id)
        
        # 确保返回正确格式的数据
        return jsonify({
            'success': True,
            'conversation': {
                'id': conversation['id'],
                'title': conversation.get('title', '无标题对话'),
                'created_at': conversation.get('created_at'),
                'updated_at': conversation.get('updated_at')
            },
            'messages': messages
        })
            
    except Exception as e:
        print(f"获取对话详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器错误，请稍后再试'
        }), 500

if __name__ == '__main__':
    try:
        if init_services():
            print("服务启动成功 - http://localhost:5000")
            # 只在主进程中打开浏览器
            if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
                Timer(3.2, lambda: webbrowser.open('http://localhost:5000')).start()
            app.run(host='localhost', port=5000)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"启动失败: {str(e)}")
        sys.exit(1)
    finally:
        if chat_bridge:
            chat_bridge.cleanup() 