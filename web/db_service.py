import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from config import POOL_CONFIG
import os
import time
from functools import wraps

class DatabaseService:
    _instance = None
    _pool = None
    _max_retries = 3  # 最大重试次数

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseService()
        return cls._instance

    def __init__(self):
        self.init_pool()
        self.init_tables()

    def init_pool(self):
        """初始化数据库连接池"""
        try:
            print("正在连接数据库...")
            self._pool = PooledDB(
                creator=pymysql,         # 使用pymysql作为数据库连接驱动
                host=POOL_CONFIG['host'],
                port=POOL_CONFIG['port'],
                user=POOL_CONFIG['user'],
                passwd=POOL_CONFIG['password'],  # 注意：这里使用passwd而不是password
                db=POOL_CONFIG['database'],      # 注意：这里使用db而不是database
                charset=POOL_CONFIG['charset'],
                cursorclass=DictCursor,  # 使用字典游标
                mincached=2,            # 初始化时，连接池中至少创建的空闲的链接
                maxcached=5             # 连接池中最多闲置的链接
            )
            print("数据库连接池初始化成功")
            
            # 测试连接
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    print("数据库连接测试成功")
                    
            return True
        except Exception as e:
            print(f"数据库连接池初始化失败: {str(e)}")
            raise

    def init_tables(self):
        """初始化数据库表"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 检查表是否存在
                    cur.execute("""
                        SELECT table_name
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE()
                        AND table_name IN ('users', 'user_settings', 'conversations', 'chat_history')
                    """)
                    existing_tables = cur.fetchall()
                    
                    # 如果所有表都存在，直接返回
                    if len(existing_tables) == 4:
                        print("数据库表已存在，跳过初始化")
                        return True
                    
                    print("正在初始化缺失的数据库表...")
                    
                    # 创建用户表（如果不存在）
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_login TIMESTAMP NULL,
                            status INT DEFAULT 1,
                            role VARCHAR(20) DEFAULT 'user'
                        )
                    """)
                    
                    # 创建用户设置表（如果不存在）
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_settings (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            theme VARCHAR(20) DEFAULT 'light',
                            language VARCHAR(10) DEFAULT 'zh-CN',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """)
                    
                    # 检查是否需要创建游客用户
                    cur.execute("SELECT id FROM users WHERE username = 'guest'")
                    if not cur.fetchone():
                        print("创建游客用户...")
                        cur.execute("""
                            INSERT INTO users (id, username, password_hash, status, role)
                            VALUES (-1, 'guest', 'guest_password', 1, 'guest')
                        """)
                    
                    # 创建对话表（如果不存在）
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS conversations (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            title VARCHAR(255),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """)
                    
                    # 创建聊天记录表（如果不存在）
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            conversation_id INT NOT NULL,
                            user_id INT NOT NULL,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """)
                    
                    conn.commit()
                    print("数据库表初始化成功")
                    
            return True
        except Exception as e:
            print(f"数据库表初始化失败: {str(e)}")
            raise

    def get_connection(self):
        """获取数据库连接"""
        try:
            return self._pool.connection()
        except Exception as e:
            print(f"获取连接失败: {str(e)}")
            # 尝试重新初始化连接池
            self.init_pool()
            return self._pool.connection()

    def save_chat(self, user_question, model_answer, user_id, conversation_id=None):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if conversation_id is None:
                # 创建新会话，关联用户
                cursor.execute(
                    "INSERT INTO conversations (user_id, created_at) VALUES (%s, NOW())",
                    (user_id,)
                )
                conversation_id = cursor.lastrowid
            
            # 保存消息
            cursor.execute("""
                INSERT INTO chat_history 
                (conversation_id, user_question, model_answer, created_at) 
                VALUES (%s, %s, %s, NOW())
            """, (conversation_id, user_question, model_answer))
            
            conn.commit()
            return {
                'conversation_id': conversation_id,
                'message_id': cursor.lastrowid
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_chat_history(self, user_id=None, conversation_id=None, keyword=None, limit=50):
        """获取聊天历史记录"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT 
                            ch.id as message_id,
                            ch.conversation_id,
                            ch.question,
                            ch.answer,
                            ch.created_at,
                            c.created_at as conversation_time
                        FROM chat_history ch
                        JOIN conversations c ON ch.conversation_id = c.id
                        WHERE ch.user_id = %s
                    """
                    params = [user_id]

                    if conversation_id:
                        query += " AND ch.conversation_id = %s"
                        params.append(conversation_id)
                    
                    if keyword:
                        query += " AND (ch.question LIKE %s OR ch.answer LIKE %s)"
                        keyword_param = f"%{keyword}%"
                        params.extend([keyword_param, keyword_param])
                    
                    # 添加排序和限制
                    query += " ORDER BY ch.created_at DESC LIMIT %s"
                    params.append(limit)
                    
                    # 执行查询
                    cur.execute(query, params)
                    results = cur.fetchall()
                    
                    return results
                    
        except Exception as e:
            print(f"获取聊天历史失败: {str(e)}")
            raise

    def search_history(self, user_id, keyword):
        """搜索聊天历史
        
        Args:
            user_id: 用户ID
            keyword: 搜索关键词
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT DISTINCT
                            ch.conversation_id,
                            c.created_at as conversation_time,
                            (
                                SELECT JSON_ARRAYAGG(
                                    JSON_OBJECT(
                                        'id', ch2.id,
                                        'question', ch2.question,
                                        'answer', ch2.answer,
                                        'created_at', ch2.created_at
                                    )
                                )
                                FROM chat_history ch2
                                WHERE ch2.conversation_id = ch.conversation_id
                                ORDER BY ch2.created_at
                            ) as messages
                        FROM chat_history ch
                        JOIN conversations c ON ch.conversation_id = c.id
                        WHERE ch.user_id = %s
                        AND (ch.question LIKE %s OR ch.answer LIKE %s)
                        ORDER BY c.created_at DESC
                    """
                    keyword_param = f"%{keyword}%"
                    cur.execute(query, (user_id, keyword_param, keyword_param))
                    results = cur.fetchall()
                    
                    return results
                    
        except Exception as e:
            print(f"搜索聊天历史失败: {str(e)}")
            raise

    def delete_chat(self, conversation_id):
        """删除指定会话的所有记录"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print(f"开始删除会话: conversation_id={conversation_id}")
            
            # 检查会话是否存在
            cursor.execute("SELECT id FROM conversations WHERE id = %s", (conversation_id,))
            if not cursor.fetchone():
                raise Exception("会话不存在")
            
            # 开始事务
            conn.start_transaction()
            
            # 先删除聊天记录
            cursor.execute("DELETE FROM chat_history WHERE conversation_id = %s", (conversation_id,))
            
            # 再删除会话
            cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            
            # 提交事务
            conn.commit()
            print(f"会话删除成功: conversation_id={conversation_id}")
            
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"删除会话失败: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_chat_by_id(self, conversation_id):
        """获取指定会话的所有消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(DictCursor)
            
            sql = """
                SELECT 
                    h.*,
                    c.created_at as conversation_start
                FROM chat_history h
                JOIN conversations c ON c.id = h.conversation_id
                WHERE h.conversation_id = %s
                ORDER BY h.created_at ASC
            """
            
            cursor.execute(sql, (conversation_id,))
            messages = cursor.fetchall()
            
            if not messages:
                return None
            
            return {
                'conversation_id': conversation_id,
                'messages': messages,
                'created_at': messages[0]['conversation_start']
            }
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def create_conversation(self, user_id):
        """创建新的对话"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO conversations (user_id, created_at) VALUES (%s, NOW())",
                        (user_id,)
                    )
                    conversation_id = cur.lastrowid
                    conn.commit()
                    return conversation_id
        except Exception as e:
            print(f"创建对话失败: {str(e)}")
            raise

    def save_chat_history(self, user_id, conversation_id=None, question=None, answer=None, force_new=False, model_id='default'):
        """
        保存聊天记录
        :param user_id: 用户ID
        :param conversation_id: 会话ID，如果为None则创建新会话
        :param question: 用户问题
        :param answer: 模型回答
        :param force_new: 是否强制创建新会话
        :param model_id: 使用的模型ID
        :return: 会话ID和消息ID
        """
        try:
            # 数据库操作
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 如果强制创建新会话或没有会话ID，创建新会话
            if force_new or not conversation_id:
                try:
                    # 创建新会话
                    cursor.execute(
                        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
                        (user_id, question[:50] if question else "新会话")
                    )
                    conversation_id = cursor.lastrowid
                    print(f"创建新会话: {conversation_id}")
                except Exception as e:
                    print(f"创建会话失败: {str(e)}")
                    return {
                        'success': False,
                        'error': str(e)
                    }
            else:
                # 更新现有会话的时间戳
                try:
                    cursor.execute(
                        "UPDATE conversations SET updated_at = NOW() WHERE id = %s AND user_id = %s",
                        (conversation_id, user_id)
                    )
                    
                    # 检查是否更新成功（受影响的行数）
                    if cursor.rowcount == 0:
                        # 如果没有更新成功，可能是会话不存在或不属于该用户，创建新会话
                        cursor.execute(
                            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
                            (user_id, question[:50] if question else "新会话")
                        )
                        conversation_id = cursor.lastrowid
                        print(f"会话不存在或无权访问，创建新会话: {conversation_id}")
                except Exception as e:
                    print(f"更新会话时间戳失败: {str(e)}")
            
            # 保存聊天记录
            try:
                # 插入聊天记录
                cursor.execute(
                    """
                    INSERT INTO chat_history 
                    (conversation_id, question, answer, created_at, model_id) 
                    VALUES (%s, %s, %s, NOW(), %s)
                    """,
                    (conversation_id, question, answer, model_id)
                )
                message_id = cursor.lastrowid
                print(f"保存聊天记录成功: {message_id}")
            except Exception as e:
                print(f"保存聊天记录失败: {str(e)}")
                return {
                    'success': False,
                    'error': str(e)
                }
            
            # 提交事务
            conn.commit()
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'message_id': message_id
            }
            
        except Exception as e:
            print(f"保存聊天记录失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()

    def get_latest_conversation(self, user_id):
        """获取用户最新的对话"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cur:
                    cur.execute("""
                        SELECT id, title, created_at 
                        FROM conversations 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (user_id,))
                    return cur.fetchone()
        except Exception as e:
            print(f"获取最新对话失败: {str(e)}")
            return None

    def get_conversation(self, conversation_id, user_id):
        """获取特定对话"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM conversations 
                        WHERE id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    return cur.fetchone()
        except Exception as e:
            print(f"获取对话失败: {str(e)}")
            return None

    def delete_conversation(self, conversation_id, user_id):
        """删除对话及其所有消息"""
        try:
            with self.get_connection() as conn:
                # 首先检查对话是否存在且属于该用户
                with conn.cursor(DictCursor) as cur:
                    cur.execute("""
                        SELECT id FROM conversations 
                        WHERE id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    conversation = cur.fetchone()
                    
                    if not conversation:
                        print(f"对话 {conversation_id} 不存在或不属于用户 {user_id}")
                        return False
                
                with conn.cursor() as cur:
                    # 记录删除操作
                    print(f"删除用户 {user_id} 的对话 {conversation_id} 相关记录")
                    
                    # 先删除聊天记录
                    cur.execute("""
                        DELETE FROM chat_history 
                        WHERE conversation_id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    deleted_messages = cur.rowcount
                    print(f"已删除 {deleted_messages} 条聊天记录")
                    
                    # 再删除对话
                    cur.execute("""
                        DELETE FROM conversations 
                        WHERE id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    deleted_conversations = cur.rowcount
                    print(f"已删除 {deleted_conversations} 条对话记录")
                    
                    conn.commit()
                    return deleted_conversations > 0
        except Exception as e:
            print(f"删除对话失败: {str(e)}")
            return False

    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cur:
                    cur.execute("""
                        SELECT id, username, password_hash, created_at, last_login, status, role
                        FROM users 
                        WHERE username = %s
                    """, (username,))
                    return cur.fetchone()
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            raise

    def create_user(self, username, password_hash):
        """创建新用户"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cur:
                    # 检查用户名是否已存在
                    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if cur.fetchone():
                        raise Exception("用户名已存在")

                    # 创建新用户
                    cur.execute("""
                        INSERT INTO users (username, password_hash, status, role, created_at)
                        VALUES (%s, %s, 1, 'user', NOW())
                        RETURNING id, username, created_at, status, role
                    """, (username, password_hash))
                    conn.commit()
                    return cur.fetchone()
        except Exception as e:
            print(f"创建用户失败: {str(e)}")
            raise

    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE users 
                        SET last_login = NOW() 
                        WHERE id = %s
                    """, (user_id,))
                    conn.commit()
        except Exception as e:
            print(f"更新登录时间失败: {str(e)}")
            raise

    def check_user_status(self, user_id):
        """检查用户状态"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cur:
                    cur.execute("""
                        SELECT status, role 
                        FROM users 
                        WHERE id = %s
                    """, (user_id,))
                    result = cur.fetchone()
                    return result if result else {'status': 0, 'role': None}
        except Exception as e:
            print(f"检查用户状态失败: {str(e)}")
            raise

    def get_user_conversations(self, user_id):
        """获取用户的所有对话"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, title, created_at, updated_at
                        FROM conversations
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                    """, (user_id,))
                    conversations = cursor.fetchall()
                    return conversations
        except Exception as e:
            print(f"获取用户对话失败: {str(e)}")
            return []

    def get_conversation_messages(self, user_id, conversation_id):
        """获取特定对话的所有消息"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cursor:
                    # 首先验证这个对话属于该用户
                    cursor.execute("""
                        SELECT id FROM conversations 
                        WHERE id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    if not cursor.fetchone():
                        return []  # 对话不存在或不属于该用户
                    
                    # 获取所有消息
                    cursor.execute("""
                        SELECT question, answer, created_at
                        FROM chat_history
                        WHERE conversation_id = %s
                        ORDER BY created_at
                    """, (conversation_id,))
                    messages = cursor.fetchall()
                    
                    # 转换为统一格式
                    formatted_messages = []
                    for msg in messages:
                        formatted_messages.append({
                            'role': 'user',
                            'content': msg['question'],
                            'timestamp': msg['created_at'].isoformat()
                        })
                        formatted_messages.append({
                            'role': 'assistant',
                            'content': msg['answer'],
                            'timestamp': msg['created_at'].isoformat()
                        })
                    
                    return formatted_messages
        except Exception as e:
            print(f"获取对话消息失败: {str(e)}")
            return []

    def check_user_exists(self, user_id):
        """检查用户ID是否存在于数据库中"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM users WHERE id = %s", (user_id,))
                    result = cur.fetchone()
                    # 使用字典访问方式
                    count = result['count'] if result else 0
                    return count > 0
        except Exception as e:
            print(f"检查用户存在性失败: {str(e)}")
            return False

    def update_conversation_title(self, conversation_id, title):
        """更新对话标题"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE conversations SET title = %s WHERE id = %s",
                        (title, conversation_id)
                    )
                    conn.commit()
                    return True
        except Exception as e:
            print(f"更新对话标题失败: {str(e)}")
            return False

    def is_conversation_titled(self, cursor, conversation_id):
        """检查对话是否已有标题"""
        cursor.execute(
            "SELECT title FROM conversations WHERE id = %s AND (title IS NOT NULL AND title != 'Unnamed' AND title != '新对话')",
            (conversation_id,)
        )
        result = cursor.fetchone()
        return result is not None

def db_connection(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            with self.get_connection() as conn:
                with conn.cursor(DictCursor) as cursor:  # 使用DictCursor
                    return func(self, conn, cursor, *args, **kwargs)
        except Exception as e:
            print(f"数据库操作失败: {str(e)}")
            raise
    return wrapper 