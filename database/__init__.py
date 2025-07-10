"""
数据库包初始化文件
导入主要的类和函数供外部使用
"""

from .config import DatabaseConfig, get_config, DEFAULT_CONFIG
from .models import *
from .db_utils import (
    DatabaseManager, StudentDAO, CrewBaseDAO, CrewWorkFileDAO, MajorDAO,
    db_manager, student_dao, crew_base_dao, crew_work_file_dao, major_dao,
    init_database, get_student_dao, get_crew_base_dao, get_crew_work_file_dao, get_major_dao
)

__all__ = [
    # 配置相关
    'DatabaseConfig', 'get_config', 'DEFAULT_CONFIG',
    
    # 模型相关
    'Student', 'Major', 'CrewBase', 'CrewMember', 'CrewLeader', 'StudentRecord',
    'CrewWorklist', 'CrewWorkFile', 'StudentIntendedMajor', 'StudentPromiseMajor',
    'AdmissionStatusEnum', 'RecordTypeEnum', 'TaskStatusEnum', 'TaskPriorityEnum',
    'AccessPermissionEnum',
    
    # 数据库操作相关
    'DatabaseManager', 'StudentDAO', 'CrewBaseDAO', 'CrewWorkFileDAO', 'MajorDAO',
    'db_manager', 'student_dao', 'crew_base_dao', 'crew_work_file_dao', 'major_dao',
    'init_database', 'get_student_dao', 'get_crew_base_dao', 'get_crew_work_file_dao', 'get_major_dao'
] 