"""
数据库配置文件
包含MySQL数据库连接参数和相关配置
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "password"
    database: str = "nju_recruitment"
    charset: str = "utf8mb4"
    autocommit: bool = True
    max_connections: int = 20
    
    def get_connection_url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
    
    def get_connection_params(self) -> dict:
        """获取数据库连接参数字典"""
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': self.database,
            'charset': self.charset,
            'autocommit': self.autocommit
        }

# 开发环境配置
DEV_CONFIG = DatabaseConfig(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "password"),
    database=os.getenv("DB_NAME", "nju_recruitment"),
    charset="utf8mb4",
    autocommit=True,
    max_connections=20
)

# 生产环境配置
PROD_CONFIG = DatabaseConfig(
    host=os.getenv("PROD_DB_HOST", "localhost"),
    port=int(os.getenv("PROD_DB_PORT", 3306)),
    user=os.getenv("PROD_DB_USER", "root"),
    password=os.getenv("PROD_DB_PASSWORD", "password"),
    database=os.getenv("PROD_DB_NAME", "nju_recruitment"),
    charset="utf8mb4",
    autocommit=True,
    max_connections=50
)

# 测试环境配置
TEST_CONFIG = DatabaseConfig(
    host=os.getenv("TEST_DB_HOST", "localhost"),
    port=int(os.getenv("TEST_DB_PORT", 3306)),
    user=os.getenv("TEST_DB_USER", "root"),
    password=os.getenv("TEST_DB_PASSWORD", "password"),
    database=os.getenv("TEST_DB_NAME", "nju_recruitment_test"),
    charset="utf8mb4",
    autocommit=True,
    max_connections=10
)

def get_config(env: str = "dev") -> DatabaseConfig:
    """
    根据环境获取数据库配置
    
    Args:
        env: 环境名称 ('dev', 'prod', 'test')
        
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    configs = {
        "dev": DEV_CONFIG,
        "prod": PROD_CONFIG,
        "test": TEST_CONFIG
    }
    
    return configs.get(env.lower(), DEV_CONFIG)

# 默认使用开发环境配置
DEFAULT_CONFIG = get_config(os.getenv("ENV", "dev")) 