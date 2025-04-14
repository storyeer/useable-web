from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import jwt
from datetime import datetime, timedelta
from config import DB_SERVICE_CONFIG, JWT_CONFIG  # 使用简化的数据库配置

class UserService:
    SECRET_KEY = 'your-secret-key'  # 请更换为安全的密钥
    
    def __init__(self):
        try:
            print("正在连接数据库...")
            # 使用简单的数据库连接而不是连接池
            self.db = mysql.connector.connect(**DB_SERVICE_CONFIG)
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            raise

    def verify_token(self, token):
        """验证 JWT token"""
        try:
            # 解码 token
            payload = jwt.decode(
                token,
                JWT_CONFIG['SECRET_KEY'],
                algorithms=["HS256"]
            )
            
            # 检查 token 是否过期
            exp = datetime.fromtimestamp(payload['exp'])
            if exp < datetime.utcnow():
                print("token已过期")
                return None
            
            # 确保返回的用户数据包含id字段(与user_id保持一致)
            if 'user_id' in payload and 'id' not in payload:
                payload['id'] = payload['user_id']
                
            # 尝试同步创建用户到数据库（如果不存在）
            try:
                if 'user_id' in payload and 'username' in payload:
                    user_id = payload['user_id']
                    username = payload['username']
                    
                    # 连接数据库
                    conn = mysql.connector.connect(**DB_SERVICE_CONFIG)
                    cursor = conn.cursor(dictionary=True)
                    
                    # 检查用户是否存在
                    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                    user_exists = cursor.fetchone()
                    
                    # 如果用户不存在，创建新用户
                    if not user_exists:
                        print(f"用户 {username}(ID:{user_id}) 不存在，正在创建...")
                        # 使用临时密码，实际情况应该提示用户重新设置密码
                        temp_password = f"temp_{user_id}_{int(datetime.now().timestamp())}"
                        password_hash = generate_password_hash(temp_password)
                        
                        cursor.execute("""
                            INSERT INTO users (id, username, password_hash, created_at, status, role)
                            VALUES (%s, %s, %s, NOW(), 1, 'user')
                        """, (user_id, username, password_hash))
                        
                        conn.commit()
                        print(f"用户 {username}(ID:{user_id}) 已创建")
                    
                    cursor.close()
                    conn.close()
            except Exception as e:
                print(f"同步创建用户失败: {str(e)}")
                # 失败不影响返回token信息
                
            return payload
            
        except jwt.ExpiredSignatureError:
            print("token已过期")
            return None
        except jwt.InvalidTokenError as e:
            print(f"token验证失败: {str(e)}")
            return None

    def get_user(self, user_id):
        """获取用户信息"""
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(
                'SELECT id, username, created_at, status, role FROM users WHERE id = %s',
                (user_id,)
            )
            user = cursor.fetchone()
            cursor.close()
            return user
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return None

    def authenticate(self, username, password):
        """验证用户登录"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # 查询用户信息
            cursor.execute("""
                SELECT id, username, password_hash, created_at, status, role 
                FROM users 
                WHERE username = %s AND status = 1
            """, (username,))
            
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                # 更新最后登录时间
                cursor.execute("""
                    UPDATE users 
                    SET last_login = NOW() 
                    WHERE id = %s
                """, (user['id'],))
                self.db.commit()
                
                # 返回用户信息（排除敏感字段）
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None
                }
            return None
            
        except Exception as e:
            print(f"用户验证失败: {str(e)}")
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()

    def register(self, username, password):
        """用户注册"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {
                    "success": False,
                    "error": "用户名已存在"
                }
            
            # 创建新用户
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, created_at, status, role)
                VALUES (%s, %s, NOW(), 1, 'user')
            """, (username, hashed_password))
            
            self.db.commit()
            user_id = cursor.lastrowid
            
            # 获取新创建的用户信息
            cursor.execute("""
                SELECT id, username, created_at, role
                FROM users WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            # 生成token
            token = self.generate_token(user)
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role']
                }
            }
            
        except Exception as e:
            print(f"注册失败: {str(e)}")
            if self.db:
                self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if 'cursor' in locals():
                cursor.close()

    def is_admin(self, user_id):
        """检查用户是否是管理员"""
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT role FROM users 
                WHERE id = %s AND status = 1
            """, (user_id,))
            
            user = cursor.fetchone()
            return user and user['role'] == 'admin'
        except Exception as e:
            print(f"检查用户是否是管理员失败: {str(e)}")
            return False

    def get_all_users(self, admin_id):
        """获取所有用户列表（仅管理员可用）"""
        if not self.is_admin(admin_id):
            return {
                "success": False,
                "error": "无权限访问"
            }

        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, username, created_at, last_login, status, role
                FROM users 
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            return {
                "success": True,
                "users": users
            }
        except Exception as e:
            print(f"获取所有用户列表失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_user_status(self, admin_id, user_id, status):
        """更新用户状态（仅管理员可用）"""
        if not self.is_admin(admin_id):
            return {
                "success": False,
                "error": "无权限操作"
            }

        try:
            cursor = self.db.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET status = %s 
                WHERE id = %s AND role != 'admin'
            """, (status, user_id))
            
            self.db.commit()
            return {
                "success": True,
                "message": "更新成功"
            }
        except Exception as e:
            print(f"更新用户状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def login(self, username, password):
        """用户登录"""
        try:
            # 获取用户信息
            user = self.get_user(username)
            if not user:
                return {
                    "success": False,
                    "error": "用户名或密码错误"
                }
            
            # 验证密码
            if not check_password_hash(user['password_hash'], password):
                return {
                    "success": False,
                    "error": "用户名或密码错误"
                }
            
            # 检查用户状态
            if user['status'] != 1:
                return {
                    "success": False,
                    "error": "账号已被禁用"
                }
            
            # 更新最后登录时间
            self.update_last_login(user['id'])
            
            # 生成token
            token = self.generate_token(user)
            
            return {
                "success": True,
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role']
                }
            }
        
        except Exception as e:
            print(f"登录失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_token(self, user):
        """生成 JWT token"""
        try:
            # 设置过期时间
            exp = datetime.utcnow() + timedelta(days=JWT_CONFIG['EXPIRE_DAYS'])
            
            # 创建 token 载荷
            payload = {
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': exp
            }
            
            # 生成 token
            token = jwt.encode(
                payload,
                JWT_CONFIG['SECRET_KEY'],
                algorithm="HS256"
            )
            
            return token
        except Exception as e:
            print(f"生成token失败: {str(e)}")
            raise

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    def update_user_profile(self, user_id, **kwargs):
        """更新用户资料"""
        try:
            # 构建更新SQL
            update_fields = []
            params = []
            
            if 'email' in kwargs and kwargs['email']:
                update_fields.append("email = %s")
                params.append(kwargs['email'])
            
            if 'display_name' in kwargs and kwargs['display_name']:
                update_fields.append("display_name = %s")
                params.append(kwargs['display_name'])
            
            if not update_fields:
                return {"success": False, "error": "没有需要更新的字段"}
            
            # 添加用户ID
            params.append(user_id)
            
            # 执行更新
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(
                f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s",
                params
            )
            self.db.commit()
            
            # 获取更新后的用户信息
            cursor.execute("SELECT id, username, email, display_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            cursor.close()
            
            return {
                "success": True,
                "user": user
            }
        except Exception as e:
            print(f"更新用户资料失败: {str(e)}")
            if self.db:
                self.db.rollback()
            return {"success": False, "error": str(e)}

    def update_password(self, user_id, current_password, new_password):
        """更新用户密码"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # 验证当前密码
            cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {"success": False, "error": "用户不存在"}
            
            if not check_password_hash(user['password'], current_password):
                return {"success": False, "error": "当前密码不正确"}
            
            # 更新密码
            hashed_password = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (hashed_password, user_id)
            )
            self.db.commit()
            cursor.close()
            
            return {"success": True}
        except Exception as e:
            print(f"更新密码失败: {str(e)}")
            if self.db:
                self.db.rollback()
            return {"success": False, "error": str(e)} 