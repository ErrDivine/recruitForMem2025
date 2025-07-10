"""
数据库模型类
对应 information_eg.py 中的数据结构和数据库表
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class AdmissionStatusEnum(Enum):
    """录取状态枚举"""
    UNPROCESSED = "未处理"
    ADMITTED = "已录取"
    SLIDE = "已滑档"
    TRANSFERRING = "调剂中"

class RecordTypeEnum(Enum):
    """记录类型枚举"""
    CONSULTATION = "咨询"
    INTERVIEW = "面试"
    ADMISSION = "录取"
    TRANSFER = "调剂"
    OTHER = "其他"

class TaskStatusEnum(Enum):
    """任务状态枚举"""
    PENDING = "待处理"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"

class TaskPriorityEnum(Enum):
    """任务优先级枚举"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    URGENT = "紧急"

class AccessPermissionEnum(Enum):
    """文件访问权限枚举"""
    PRIVATE = "private"
    CREW_ONLY = "crew_only"
    PUBLIC = "public"

@dataclass
class Major:
    """专业信息模型"""
    id: Optional[int] = None
    major_code: str = ""
    major_name: str = ""
    category: str = "综合"  # '理科', '文科', '综合'
    quota: int = 0
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class Student:
    """学生信息模型 - 对应 information_eg.py 中的 Student 类"""
    id: Optional[int] = None
    student_id: Optional[str] = None
    name: str = ""  # 考生姓名
    high_school: str = ""  # 考生高中学校名
    category: bool = True  # 考生类别：False-文科生，True-理科生
    total_score: float = 0.0  # 考生高考总分
    chinese_score: float = 0.0  # 考生高考语文分数
    math_score: float = 0.0  # 考生高考数学分数
    overall_rank: int = 0  # 考生省排名
    sfp_university: str = ""  # 考生强基学校（如果没有就是空字符串）
    tele_student: str = ""  # 考生自己联系电话
    tele_parent: str = ""  # 考生家长联系电话
    transferable: bool = False  # 考生是否服从调剂
    level: int = 0  # 考生意向等级，0-100分
    admission_status: AdmissionStatusEnum = AdmissionStatusEnum.UNPROCESSED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据（不直接存在数据库中，通过关联表获取）
    intended_majors: List[str] = None  # 考生意向专业列表（专业名字符串）
    promise_majors: List[str] = None   # 招生组对考生的承诺专业列表
    due_chargers: List['CrewBase'] = None  # 考生负责人列表
    records: List['StudentRecord'] = None  # 沟通记录列表
    
    def __post_init__(self):
        if self.intended_majors is None:
            self.intended_majors = []
        if self.promise_majors is None:
            self.promise_majors = []
        if self.due_chargers is None:
            self.due_chargers = []
        if self.records is None:
            self.records = []
    
    @property
    def total_score_int(self) -> int:
        """获取总分的整数值"""
        return int(self.total_score)
    
    @property
    def rank_int(self) -> int:
        """获取排名的整数值"""
        return int(self.overall_rank)
    
    @property
    def math_score_int(self) -> int:
        """获取数学分数的整数值"""
        return int(self.math_score)
    
    @property
    def chinese_score_int(self) -> int:
        """获取语文分数的整数值"""
        return int(self.chinese_score)
    
    @property
    def math_chinese_sum(self) -> int:
        """获取数学+语文总分"""
        return self.math_score_int + self.chinese_score_int
    
    @property
    def math_chinese_max(self) -> int:
        """获取数学和语文中的最高分"""
        return max(self.math_score_int, self.chinese_score_int)
    
    @property
    def category_display(self) -> str:
        """获取类别显示文本"""
        return "理科生" if self.category else "文科生"
    
    def is_high_score_student(self, score_threshold: int = 650) -> bool:
        """判断是否为高分考生"""
        return self.total_score_int >= score_threshold
    
    def is_top_rank_student(self, rank_threshold: int = 200) -> bool:
        """判断是否为高排名考生"""
        return self.rank_int <= rank_threshold

@dataclass
class CrewBase:
    """工作人员基础模型 - 对应 information_eg.py 中的 crew 基类"""
    id: Optional[int] = None
    name: str = ""  # 工作人员名字
    account: str = ""  # 工作人员账号
    password: str = ""  # 账号密码
    email: str = ""  # 工作人员邮箱
    color: str = ""  # 颜色标识
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据（不直接存在数据库中，通过关联表获取）
    worklist: List[str] = None  # 工作人员需要联系的学生名字列表
    work_files: List['CrewWorkFile'] = None  # 工作文件列表
    
    def __post_init__(self):
        if self.worklist is None:
            self.worklist = []
        if self.work_files is None:
            self.work_files = []

@dataclass
class CrewMember:
    """普通工作人员模型 - 对应 information_eg.py 中的 crew_member 类"""
    id: Optional[int] = None
    crew_base_id: int = 0
    member_level: int = 1  # 成员等级
    supervisor_id: Optional[int] = None  # 上级主管ID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联的基础信息
    base_info: Optional[CrewBase] = None

@dataclass
class CrewLeader:
    """工作人员负责人模型 - 对应 information_eg.py 中的 crew_leader 类"""
    id: Optional[int] = None
    crew_base_id: int = 0
    department: str = ""  # 负责部门
    authority_level: int = 1  # 权限等级
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联的基础信息
    base_info: Optional[CrewBase] = None

@dataclass
class StudentIntendedMajor:
    """学生意向专业关联模型 - 专业名字符串列表"""
    id: Optional[int] = None
    student_id: int = 0
    major_name: str = ""  # 专业名（字符串）
    priority: int = 0
    created_at: Optional[datetime] = None

@dataclass
class StudentPromiseMajor:
    """学生承诺专业关联模型 - 招生组承诺专业列表"""
    id: Optional[int] = None
    student_id: int = 0
    major_name: str = ""  # 招生组对考生的承诺专业名
    priority: int = 0
    created_at: Optional[datetime] = None

@dataclass
class StudentDueCharger:
    """学生负责人关联模型"""
    id: Optional[int] = None
    student_id: int = 0
    crew_base_id: int = 0  # 负责人ID（可以是member或leader）
    assigned_at: Optional[datetime] = None
    is_primary: bool = False

@dataclass
class StudentRecord:
    """学生沟通记录模型 - 格式：[联系时间,联系人]->沟通内容摘要"""
    id: Optional[int] = None
    student_id: int = 0
    contact_time: datetime = None  # 联系时间
    contact_person: str = ""  # 联系人
    content_summary: str = ""  # 沟通内容摘要
    record_type: RecordTypeEnum = RecordTypeEnum.OTHER
    operator_id: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class CrewWorklist:
    """工作人员联系学生列表 - 由考生名字组成的列表"""
    id: Optional[int] = None
    crew_base_id: int = 0
    student_name: str = ""  # 需要联系的考生名字
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    notes: str = ""  # 备注信息
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class CrewWorkFile:
    """工作文件模型 - 支持网页文件访问和在线查看"""
    id: Optional[int] = None
    crew_base_id: int = 0
    file_name: str = ""  # 文件显示名称
    file_original_name: str = ""  # 原始文件名
    file_path: str = ""  # 服务器文件存储路径
    file_url: str = ""  # 文件访问URL（用于网页打开）
    file_size: int = 0  # 文件大小（字节）
    file_type: str = ""  # 文件类型/扩展名
    mime_type: str = ""  # MIME类型（用于浏览器识别）
    description: str = ""  # 文件描述
    access_permission: AccessPermissionEnum = AccessPermissionEnum.PRIVATE  # 访问权限
    is_viewable_online: bool = True  # 是否可在线查看
    download_count: int = 0  # 下载次数
    last_accessed: Optional[datetime] = None  # 最后访问时间
    upload_time: Optional[datetime] = None

# 模型映射字典，用于数据库操作
MODEL_MAPPING = {
    'majors': Major,
    'students': Student,
    'crew_base': CrewBase,
    'crew_members': CrewMember,
    'crew_leaders': CrewLeader,
    'student_intended_majors': StudentIntendedMajor,
    'student_promise_majors': StudentPromiseMajor,
    'student_due_chargers': StudentDueCharger,
    'student_records': StudentRecord,
    'crew_worklist': CrewWorklist,
    'crew_work_files': CrewWorkFile
} 