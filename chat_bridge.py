from model_service import ModelService
from db_service import DatabaseService
from user_service import UserService
import time
from config import DB_SERVICE_CONFIG, MODEL_CONFIG
import uuid
import traceback

# 配置模型服务
USE_LOCAL_MODEL = True
MODEL_PATH = "D:/DMX/Qwen2.5-0.5B-Instruct"

class ChatBridge:
    def __init__(self):
        self.model_service = None
        self.db_service = None
        self.user_service = None
        self.init_services()

    def init_services(self):
        """初始化所有服务"""
        print("开始初始化服务...")
        try:
            # 初始化模型服务
            print("正在初始化模型服务...")
            self.init_model_service()
            
            # 初始化数据库服务
            print("正在初始化数据库服务...")
            self.init_db_service()
            
            # 初始化用户服务
            print("正在初始化用户服务...")
            self.user_service = UserService()
            
            return True
        except Exception as e:
            print(f"初始化服务失败: {str(e)}")
            return False

    def init_model_service(self):
        try:
            print("正在加载本地模型...")
            self.model_service = ModelService(
                use_local=MODEL_CONFIG['use_local'],
                model_path=MODEL_CONFIG['model_path']
            )
            
            # 初始化可用模型字典
            self.available_models = {
                '1': MODEL_CONFIG['model_path'],  # Qwen2.5-0.5B-Instruct
                '2': "D:/DMX/DeepSeek-R1-Distill-Qwen-14B"  # DeepSeek-R1-Distill-Qwen-14B
            }
            
            print("模型加载完成")
        except Exception as e:
            print(f"模型加载错误: {str(e)}")
            raise
    
    def init_db_service(self):
        print("正在初始化数据库服务...")
        try:
            from database_service import DatabaseService  # 修改为正确的导入路径
            self.db_service = DatabaseService()
            print("数据库服务初始化成功")
        except Exception as e:
            print(f"数据库服务初始化失败: {str(e)}")
            raise

    def handle_chat(self, message, user_id, conversation_id=None, force_new=False, model_id='1'):
        """
        处理用户聊天消息
        :param message: 用户消息
        :param user_id: 用户ID
        :param conversation_id: 会话ID，如果为None则创建新会话或使用最近的会话
        :param force_new: 是否强制创建新会话，用于用户主动点击新建对话的情况
        :param model_id: 使用的模型ID，默认为'1'
        """
        try:
            # 根据选择的模型生成回答
            if model_id in self.available_models:
                print(f"使用模型 {model_id}，路径: {self.available_models[model_id]}")
                # 临时创建一个新的模型服务实例
                temp_model_service = ModelService(
                    use_local=True,
                    model_path=self.available_models[model_id]
                )
                result = temp_model_service.generate_answer(message)
            else:
                # 使用默认模型
                print(f"未知模型ID {model_id}，使用默认模型")
                result = self.model_service.generate_answer(message)
            
            if not result.get('success'):
                return result
                
            answer = result.get('answer')
            
            # 保存聊天记录
            try:
                # 使用数据库服务保存记录
                save_result = self.db_service.save_chat_history(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    question=message,
                    answer=answer,
                    force_new=force_new,  # 传递 force_new 参数
                    model_id=model_id  # 保存使用的模型信息
                )
                
                # 检查 save_result 是字典还是布尔值
                if isinstance(save_result, dict):
                    # 新版本返回字典
                    if not save_result.get('success', False):
                        print(f"警告: 保存聊天记录失败: {save_result.get('error', '未知错误')}")
                        return {
                            'success': True,
                            'answer': answer,
                            'conversation_id': conversation_id
                        }
                    return {
                        'success': True,
                        'answer': answer,
                        'conversation_id': save_result.get('conversation_id', conversation_id)
                    }
                else:
                    # 旧版本返回布尔值
                    if not save_result:
                        print("警告: 保存聊天记录失败")
                    return {
                        'success': True,
                        'answer': answer,
                        'conversation_id': conversation_id
                    }
                    
            except Exception as db_error:
                print(f"保存聊天记录失败: {str(db_error)}")
                # 继续返回答案，即使保存失败
                return {
                    'success': True,
                    'answer': answer,
                    'conversation_id': conversation_id
                }
                
        except Exception as e:
            print(f"处理聊天消息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def handle_trial_chat(self, message, model_id='1'):
        """处理游客模式的聊天请求"""
        try:
            if not self.model_service:
                print("模型服务未初始化")
                return {
                    "success": False,
                    "error": "模型服务未初始化"
                }

            print(f"收到游客问题: {message}，使用模型: {model_id}")
            
            # 根据选择的模型生成回答
            if model_id in self.available_models:
                print(f"使用模型 {model_id}，路径: {self.available_models[model_id]}")
                # 临时创建一个新的模型服务实例
                temp_model_service = ModelService(
                    use_local=True,
                    model_path=self.available_models[model_id]
                )
                result = temp_model_service.generate_answer(message)
            else:
                # 使用默认模型
                print(f"未知模型ID {model_id}，使用默认模型")
                result = self.model_service.generate_answer(message)
                
            print(f"模型返回结果: {result}")
            
            if result.get("success"):
                try:
                    # 创建一个游客用户ID（使用固定ID，如-1表示游客）
                    guest_user_id = -1
                    
                    # 获取最新的会话ID（如果存在）
                    latest_conversation = self.db_service.get_latest_conversation(guest_user_id)
                    conversation_id = latest_conversation['id'] if latest_conversation else None
                    
                    # 保存聊天记录
                    save_result = self.db_service.save_chat_history(
                        user_id=guest_user_id,
                        conversation_id=conversation_id,
                        question=message,
                        answer=result["answer"],
                        model_id=model_id  # 保存使用的模型信息
                    )
                    print(f"游客聊天记录保存成功: {save_result}")
                except Exception as e:
                    print(f"保存游客聊天记录失败: {str(e)}")
                    # 即使保存失败也返回答案
            
            return result
            
        except Exception as e:
            print(f"处理游客聊天请求失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_history(self, user_id, conversation_id=None):
        try:
            history = self.db_service.get_chat_history(user_id, conversation_id)
            return {
                "success": True,
                "history": history
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete_history(self, conversation_id, user_id):
        """删除聊天历史"""
        try:
            self.db_service.delete_chat_history(conversation_id, user_id)
            return {
                "success": True,
                "message": "删除成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'model_service') and self.model_service:
                self.model_service.cleanup()
            if hasattr(self, 'db_service') and self.db_service:
                self.db_service.cleanup()
            if hasattr(self, 'user_service') and self.user_service:
                self.user_service.cleanup()
        except Exception as e:
            print(f"清理资源时发生错误: {str(e)}")

    def guest_chat(self, message, conversation_id=None):
        """游客聊天功能 - 仅在内存中保存当前会话"""
        try:
            # 生成一个新的会话ID（如果没有提供）
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # 使用正确的方法名称调用模型服务
            if hasattr(self.model_service, 'generate_answer'):
                result = self.model_service.generate_answer(message)
                
                if result.get("success"):
                    answer = result.get("answer")
                else:
                    print(f"模型生成失败: {result.get('error')}")
                    answer = "抱歉，处理您的请求时出现了问题。"
            else:
                print("警告: 找不到ModelService.generate_answer方法")
                answer = "很抱歉，我暂时无法处理您的请求。模型服务当前不可用。"
            
            # 临时存储到内存中 - 不保存到数据库
            try:
                # 将对话临时存储到全局变量或缓存中
                if not hasattr(self, '_guest_chats'):
                    self._guest_chats = {}
                
                if conversation_id not in self._guest_chats:
                    self._guest_chats[conversation_id] = []
                    
                self._guest_chats[conversation_id].append({
                    'role': 'user',
                    'content': message,
                    'timestamp': time.time()
                })
                
                self._guest_chats[conversation_id].append({
                    'role': 'assistant',
                    'content': answer,
                    'timestamp': time.time()
                })
            except Exception as e:
                print(f"临时存储聊天历史失败: {str(e)}")
            
            return {
                'success': True,
                'answer': answer,
                'conversation_id': conversation_id
            }
        except Exception as e:
            print(f"游客聊天出错: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': '服务暂时不可用，请稍后再试',
                'conversation_id': conversation_id if conversation_id else None
            }

    def user_chat(self, message, conversation_id=None, user_id=None):
        """注册用户聊天功能 - 将聊天记录保存到数据库"""
        try:
            # 生成一个新的会话ID（如果没有提供）
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # 使用正确的方法名称调用模型服务
            if hasattr(self.model_service, 'generate_answer'):
                result = self.model_service.generate_answer(message)
                
                if result.get("success"):
                    answer = result.get("answer")
                else:
                    print(f"模型生成失败: {result.get('error')}")
                    answer = "抱歉，处理您的请求时出现了问题。"
            else:
                print("警告: 找不到ModelService.generate_answer方法")
                answer = "很抱歉，我暂时无法处理您的请求。模型服务当前不可用。"
            
            # 保存到数据库
            try:
                if user_id and hasattr(self, 'db_service') and self.db_service:
                    # 使用数据库服务保存聊天历史
                    if hasattr(self.db_service, 'save_chat_history'):
                        self.db_service.save_chat_history(user_id, conversation_id, message, answer)
                    elif hasattr(self.db_service, 'save_chat'):
                        self.db_service.save_chat(
                            user_id=user_id,
                            user_question=message,
                            model_answer=answer,
                            session_id=conversation_id
                        )
                    else:
                        print("警告: 数据库服务缺少保存聊天记录的方法")
            except Exception as e:
                print(f"保存聊天历史失败: {str(e)}")
            
            return {
                'success': True,
                'answer': answer,
                'conversation_id': conversation_id
            }
        except Exception as e:
            print(f"用户聊天出错: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': '服务暂时不可用，请稍后再试',
                'conversation_id': conversation_id if conversation_id else None
            }

    def get_response(self, message):
        """获取普通回复"""
        # 实现普通对话逻辑
        return f"这是对 '{message}' 的回复"
        
    def think_deeply(self, message):
        """深度思考模式"""
        # 实现深度思考逻辑
        return f"深度思考: {message}"
        
    def search_and_respond(self, message):
        """联网搜索模式"""
        # 实现联网搜索逻辑
        return f"搜索结果: {message}"

    def process_user_chat(self, message, mode='normal'):
        """处理用户聊天消息"""
        try:
            # 根据不同模式处理消息
            if mode == 'think':
                # 深度思考模式的提示词
                prompt = f"请深入思考并详细分析以下问题：\n{message}"
            elif mode == 'search':
                # 联网搜索模式的提示词
                prompt = f"请搜索并整理相关信息来回答以下问题：\n{message}"
            else:
                # 普通对话模式
                prompt = message

            # 调用模型服务获取回答
            if hasattr(self.model_service, 'generate_answer'):
                result = self.model_service.generate_answer(prompt)
                
                if result.get("success"):
                    return {
                        'success': True,
                        'answer': result.get("answer")
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', '模型生成失败')
                    }
            else:
                return {
                    'success': False,
                    'error': '模型服务不可用'
                }
            
        except Exception as e:
            print(f"处理用户聊天消息错误: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# 全局实例
_instance = None

def get_instance():
    """获取或创建 ChatBridge 实例"""
    global _instance
    if _instance is None:
        _instance = ChatBridge()
    return _instance 