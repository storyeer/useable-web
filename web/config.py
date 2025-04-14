# 数据库服务配置
DB_SERVICE_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'audit_ai',
    'port': 3306,
    'charset': 'utf8mb4'
}

# 连接池配置
POOL_CONFIG = {
    'host': DB_SERVICE_CONFIG['host'],
    'port': DB_SERVICE_CONFIG['port'],
    'user': DB_SERVICE_CONFIG['user'],
    'password': DB_SERVICE_CONFIG['password'],
    'database': DB_SERVICE_CONFIG['database'],
    'charset': DB_SERVICE_CONFIG['charset']
}

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',  # MySQL用户名
    'password': '123456',  # MySQL密码
    'database': 'audit_ai',  # 数据库名
    'charset': 'utf8mb4'
}

# JWT配置
JWT_CONFIG = {
    'SECRET_KEY': 'your-secret-key-here',  # 请在生产环境中使用安全的密钥
    'EXPIRE_DAYS': 7
}

# 资源版本号
RESOURCE_VERSION = '1.0.0'

# 模型配置
MODEL_CONFIG = {
    'model_path': "D:/DMX/Qwen2.5-0.5B-Instruct",  # 修改为你本地的模型路径
    'use_local': True
} 