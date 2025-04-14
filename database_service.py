from mysql.connector import pooling
from config import DB_SERVICE_CONFIG

def get_db_connection():
    """获取数据库连接"""
    try:
        return pooling.MySQLConnectionPool(**DB_SERVICE_CONFIG).get_connection()
    except Exception as e:
        print(f"获取数据库连接失败: {str(e)}")
        raise

class DatabaseService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """获取 DatabaseService 的单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化数据库服务"""
        self.db = get_db_connection()
        self._ensure_table_structure()
        
    def _ensure_table_structure(self):
        """确保数据库表结构完整"""
        try:
            cursor = self.db.cursor()
            
            # 检查并添加 last_active 字段
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'last_active'
            """, (DB_SERVICE_CONFIG['database'],))
            
            if cursor.fetchone()[0] == 0:
                print("添加 last_active 字段到 users 表")
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                """)
                self.db.commit()
                print("成功添加 last_active 字段")
            
            cursor.close()
        except Exception as e:
            print(f"检查/更新表结构失败: {str(e)}")
            raise

    def check_user_exists(self, user_id):
        """检查用户是否存在且状态正常"""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT id FROM users 
                WHERE id = %s AND status = 1
            """, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            return bool(result)
        except Exception as e:
            print(f"检查用户存在失败: {str(e)}")
            return False

    def update_user_last_active(self, user_id):
        """更新用户最后活动时间"""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_active = NOW() 
                WHERE id = %s
            """, (user_id,))
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"更新用户最后活动时间失败: {str(e)}")
            return False
            
    def get_latest_conversation(self, user_id):
        """获取用户最新的会话"""
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE user_id = %s 
                ORDER BY updated_at DESC 
                LIMIT 1
            """, (user_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            print(f"获取最新会话失败: {str(e)}")
            return None
            
    def get_user_conversations(self, user_id):
        """获取用户的所有对话，只返回用户问题和日期"""
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    c.id,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT question 
                        FROM chat_history 
                        WHERE conversation_id = c.id 
                        ORDER BY created_at ASC 
                        LIMIT 1
                    ) as title
                FROM conversations c
                WHERE c.user_id = %s
                ORDER BY c.updated_at DESC
            """, (user_id,))
            conversations = cursor.fetchall()
            cursor.close()
            return conversations
        except Exception as e:
            print(f"获取用户对话列表失败: {str(e)}")
            return []

    def get_conversation(self, conversation_id, user_id):
        """获取特定对话的详细信息，并验证所有权"""
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM conversations 
                WHERE id = %s AND user_id = %s
            """, (conversation_id, user_id))
            conversation = cursor.fetchone()
            cursor.close()
            return conversation
        except Exception as e:
            print(f"获取对话详情失败: {str(e)}")
            return None

    def get_conversation_messages(self, user_id, conversation_id):
        """获取特定对话的所有消息，并验证所有权"""
        try:
            # 首先验证对话所有权
            cursor = self.db.cursor(dictionary=True)
            cursor.execute("""
                SELECT id FROM conversations 
                WHERE id = %s AND user_id = %s
            """, (conversation_id, user_id))
            
            if not cursor.fetchone():
                print(f"用户 {user_id} 无权访问对话 {conversation_id}")
                cursor.close()
                return []
            
            # 获取该对话下的所有消息
            cursor.execute("""
                SELECT 
                    ch.id,
                    ch.question,
                    ch.answer,
                    ch.created_at
                FROM chat_history ch
                INNER JOIN conversations c ON ch.conversation_id = c.id
                WHERE ch.conversation_id = %s AND c.user_id = %s
                ORDER BY ch.created_at ASC
            """, (conversation_id, user_id))
            
            messages = cursor.fetchall()
            cursor.close()
            return messages
        except Exception as e:
            print(f"获取对话消息失败: {str(e)}")
            return []

    def delete_chat_history(self, conversation_id, user_id):
        """删除特定对话及其消息，并验证所有权"""
        try:
            cursor = self.db.cursor()
            
            # 首先验证对话所有权
            cursor.execute("""
                SELECT id FROM conversations 
                WHERE id = %s AND user_id = %s
            """, (conversation_id, user_id))
            
            if not cursor.fetchone():
                print(f"用户 {user_id} 无权删除对话 {conversation_id}")
                cursor.close()
                return False
            
            # 开始事务
            self.db.start_transaction()
            
            try:
                # 删除相关的聊天记录
                cursor.execute("""
                    DELETE FROM chat_history 
                    WHERE conversation_id = %s
                """, (conversation_id,))
                
                # 删除对话
                cursor.execute("""
                    DELETE FROM conversations 
                    WHERE id = %s AND user_id = %s
                """, (conversation_id, user_id))
                
                # 提交事务
                self.db.commit()
                cursor.close()
                return True
                
            except Exception as e:
                # 回滚事务
                self.db.rollback()
                print(f"删除对话失败: {str(e)}")
                return False
                
        except Exception as e:
            print(f"删除对话操作失败: {str(e)}")
            return False

    def save_chat_history(self, user_id, conversation_id, question, answer=None, force_new=False, model_id='default'):
        """
        保存聊天记录，优化会话管理
        :param user_id: 用户ID
        :param conversation_id: 会话ID
        :param question: 问题
        :param answer: 回答
        :param force_new: 是否强制创建新会话，用于用户主动点击新建对话的情况
        :param model_id: 使用的模型ID，默认为'default'
        :return: 包含success和conversation_id的字典，或在出错时包含error信息
        """
        try:
            cursor = self.db.cursor()
            
            # 开始事务
            self.db.start_transaction()
            
            try:
                new_conversation_created = False
                
                if not conversation_id:
                    if force_new:
                        # 用户主动创建新对话，直接创建新会话
                        cursor.execute("""
                            INSERT INTO conversations 
                            (user_id, title, created_at, updated_at)
                            VALUES (%s, %s, NOW(), NOW())
                        """, (user_id, question[:20] + '...' if len(question) > 20 else question))
                        conversation_id = cursor.lastrowid
                        new_conversation_created = True
                        print(f"已为用户 {user_id} 创建新对话, ID: {conversation_id}")
                    else:
                        # 检查是否有最近的未完成会话（比如30分钟内的最后一个会话）
                        cursor.execute("""
                            SELECT id 
                            FROM conversations 
                            WHERE user_id = %s 
                            AND updated_at > DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                            ORDER BY updated_at DESC 
                            LIMIT 1
                        """, (user_id,))
                        
                        result = cursor.fetchone()
                        if result:
                            conversation_id = result[0]
                            print(f"使用最近的对话, ID: {conversation_id}")
                        else:
                            # 创建新会话
                            cursor.execute("""
                                INSERT INTO conversations 
                                (user_id, title, created_at, updated_at)
                                VALUES (%s, %s, NOW(), NOW())
                            """, (user_id, question[:20] + '...' if len(question) > 20 else question))
                            conversation_id = cursor.lastrowid
                            new_conversation_created = True
                            print(f"创建新对话, ID: {conversation_id}")
                else:
                    # 验证现有会话的所有权
                    cursor.execute("""
                        SELECT id FROM conversations 
                        WHERE id = %s AND user_id = %s
                    """, (conversation_id, user_id))
                    
                    if not cursor.fetchone():
                        raise Exception(f"用户 {user_id} 无权访问对话 {conversation_id}")
                    
                    print(f"使用现有对话, ID: {conversation_id}")
                
                # 检查chat_history表是否有model_id字段
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'chat_history' 
                    AND COLUMN_NAME = 'model_id'
                """, (DB_SERVICE_CONFIG['database'],))
                
                has_model_id = cursor.fetchone()[0] > 0
                
                if has_model_id:
                    # 保存问题和回答，包括模型ID
                    cursor.execute("""
                        INSERT INTO chat_history 
                        (conversation_id, user_id, question, answer, created_at, model_id)
                        VALUES (%s, %s, %s, %s, NOW(), %s)
                    """, (conversation_id, user_id, question, answer, model_id))
                else:
                    # 表中没有model_id字段，使用老的SQL语句
                    cursor.execute("""
                        INSERT INTO chat_history 
                        (conversation_id, user_id, question, answer, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (conversation_id, user_id, question, answer))
                    
                    # 提示可能需要添加字段
                    print("警告: chat_history表缺少model_id字段，模型信息未保存")
                
                # 更新会话的标题（如果是新创建的）和最后更新时间
                if new_conversation_created:
                    # 使用问题的前20个字符作为标题
                    title = question[:20] + '...' if len(question) > 20 else question
                    cursor.execute("""
                        UPDATE conversations 
                        SET title = %s, updated_at = NOW() 
                        WHERE id = %s
                    """, (title, conversation_id))
                else:
                    # 仅更新最后更新时间
                    cursor.execute("""
                        UPDATE conversations 
                        SET updated_at = NOW() 
                        WHERE id = %s
                    """, (conversation_id,))
                
                # 提交事务
                self.db.commit()
                
                return {
                    'success': True,
                    'conversation_id': conversation_id,
                    'is_new': new_conversation_created
                }
                
            except Exception as e:
                self.db.rollback()
                print(f"保存聊天记录失败 (事务中): {str(e)}")
                return {
                    'success': False,
                    'error': str(e)
                }
            finally:
                cursor.close()
                
        except Exception as e:
            print(f"保存聊天记录失败 (连接): {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
        except Exception as e:
            print(f"清理数据库连接失败: {str(e)}")
            
    # 其他数据库方法... 