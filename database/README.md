# 数据库模块 - 南京大学招生助手系统

本模块为南京大学招生助手系统提供完整的MySQL数据库支持，包含学生信息管理、工作人员管理、专业信息管理等功能。

## 📚 模块结构

```
database/
├── __init__.py          # 包初始化文件
├── config.py            # 数据库配置管理
├── models.py            # 数据模型定义
├── db_utils.py          # 数据库操作工具
├── create_tables.sql    # 数据库建表脚本
├── setup_database.py    # 数据库初始化脚本
├── env_example.txt      # 环境变量配置示例
└── README.md           # 本说明文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install PyMySQL==1.1.0 cryptography==41.0.7
```

### 2. 配置数据库连接

复制 `env_example.txt` 为 `.env` 文件并修改数据库连接信息：

```bash
# 基本配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=nju_recruitment
```

### 3. 初始化数据库

运行数据库初始化脚本：

```bash
cd database
python setup_database.py
```

### 4. 验证安装

```python
from database import get_student_dao, get_major_dao

# 测试数据库连接
student_dao = get_student_dao()
majors = get_major_dao().get_all_majors()
print(f"发现 {len(majors)} 个专业")
```

## 📊 数据库设计

### 核心表结构

#### 1. 学生信息表 (`students`)
- **主要字段**: 考生姓名、高中学校、文理科类别(bool)、总分、排名、电话等
- **索引**: 类别、总分、排名、录取状态
- **特点**: 支持多维度查询和统计，category为bool类型(True=理科生)

#### 2. 专业信息表 (`majors`)
- **主要字段**: 专业代码、专业名称、类别、招生名额
- **特点**: 支持文理科分类和名额管理

#### 3. 工作人员表结构（三层架构）
- **`crew_base`**: 工作人员基础信息表（姓名、账号、密码、邮箱等）
- **`crew_members`**: 普通工作人员表（继承crew_base，添加成员等级等）
- **`crew_leaders`**: 工作人员负责人表（继承crew_base，添加部门、权限等级等）

#### 4. 关联表
- `student_intended_majors` - 学生意向专业关联（专业名字符串列表）
- `student_promise_majors` - 学生承诺专业关联（招生组承诺专业列表）
- `student_due_chargers` - 学生负责人关联
- `student_records` - 学生沟通记录管理（格式：[联系时间,联系人]->沟通内容摘要）
- `crew_worklist` - 工作人员联系学生列表（由考生名字组成的列表）
- `crew_work_files` - 工作文件表（支持网页文件访问和在线查看）

## 🔧 使用指南

### 学生数据操作

```python
from database import get_student_dao, Student

student_dao = get_student_dao()

# 创建学生
student = Student(
    name="张三",
    high_school="南京市第一中学",
    category=True,  # True=理科生，False=文科生
    total_score=650.5,
    overall_rank=100,
    transferable=True,  # 是否服从调剂
    level=85  # 意向等级0-100分
)
student_id = student_dao.create_student(student)

# 查询学生
student = student_dao.get_student_by_id(student_id)
science_students = student_dao.get_students_by_category(True)  # 理科生
liberal_students = student_dao.get_students_by_category(False)  # 文科生
students = student_dao.get_students_by_score_range(600, 700)

# 批量插入
students = [student1, student2, student3]
success = student_dao.batch_insert_students(students)
```

### 专业数据操作

```python
from database import get_major_dao

major_dao = get_major_dao()

# 获取专业列表
all_majors = major_dao.get_all_majors()
science_majors = major_dao.get_majors_by_category("理科")
liberal_majors = major_dao.get_majors_by_category("文科")
```

### 工作人员和文件管理

```python
from database import get_crew_base_dao, get_crew_work_file_dao, CrewBase, CrewWorkFile

crew_dao = get_crew_base_dao()
file_dao = get_crew_work_file_dao()

# 创建工作人员基础信息
crew_base = CrewBase(
    name="张老师",
    account="teacher_zhang",
    password="hashed_password",
    email="zhang@nju.edu.cn"
)
crew_id = crew_dao.create_crew_base(crew_base)

# 创建工作文件（支持网页访问）
work_file = CrewWorkFile(
    crew_base_id=crew_id,
    file_name="招生手册.pdf",
    file_original_name="recruitment_handbook.pdf",
    file_path="/uploads/files/handbook.pdf",
    file_url="/api/files/view/123",  # 网页访问URL
    file_type="pdf",
    mime_type="application/pdf",
    access_permission=AccessPermissionEnum.CREW_ONLY,
    is_viewable_online=True
)
file_id = file_dao.create_work_file(work_file)

# 获取工作人员的文件列表
files = file_dao.get_files_by_crew(crew_id)
```

### 数据库连接管理

```python
from database import db_manager

# 使用连接上下文管理器
with db_manager.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM students")
        count = cursor.fetchone()[0]
        print(f"学生总数: {count}")
```

## 🎯 数据模型

### Student 模型
对应 `information_eg.py` 中的学生数据结构：

```python
@dataclass
class Student:
    name: str                    # 考生姓名
    high_school: str             # 考生高中学校名
    category: bool               # 考生类别：False-文科生，True-理科生
    total_score: float           # 考生高考总分
    chinese_score: float         # 考生高考语文分数
    math_score: float           # 考生高考数学分数
    overall_rank: int           # 考生省排名
    sfp_university: str         # 考生强基学校（如果没有就是空字符串）
    tele_student: str           # 考生自己联系电话
    tele_parent: str            # 考生家长联系电话
    transferable: bool          # 考生是否服从调剂
    level: int                  # 考生意向等级，0-100分
    # 关联数据
    intended_majors: List[str]  # 考生意向专业列表（专业名字符串）
    promise_majors: List[str]   # 招生组对考生的承诺专业列表
    # ... 其他字段
```

### 工作人员模型（三层架构）

```python
@dataclass
class CrewBase:
    name: str                   # 工作人员名字
    account: str               # 工作人员账号
    password: str              # 账号密码
    email: str                 # 工作人员邮箱
    worklist: List[str]        # 工作人员需要联系的学生名字列表
    work_files: List[CrewWorkFile]  # 工作文件列表

@dataclass
class CrewMember:
    crew_base_id: int          # 关联基础信息ID
    member_level: int          # 成员等级
    supervisor_id: int         # 上级主管ID

@dataclass 
class CrewLeader:
    crew_base_id: int          # 关联基础信息ID
    department: str            # 负责部门
    authority_level: int       # 权限等级
```

### 工作文件模型（支持网页访问）

```python
@dataclass
class CrewWorkFile:
    file_name: str             # 文件显示名称
    file_original_name: str    # 原始文件名
    file_path: str             # 服务器文件存储路径
    file_url: str              # 文件访问URL（用于网页打开）
    file_type: str             # 文件类型/扩展名
    mime_type: str             # MIME类型（用于浏览器识别）
    access_permission: AccessPermissionEnum  # 访问权限
    is_viewable_online: bool   # 是否可在线查看
    download_count: int        # 下载次数
```

### 枚举类型

```python
class AdmissionStatusEnum(Enum):
    UNPROCESSED = "未处理"
    ADMITTED = "已录取"
    SLIDE = "已滑档"
    TRANSFERRING = "调剂中"

class AccessPermissionEnum(Enum):
    PRIVATE = "private"        # 私有文件
    CREW_ONLY = "crew_only"    # 仅工作人员可见
    PUBLIC = "public"          # 公开文件
```

## ⚙️ 配置选项

### 环境配置

支持多环境配置（开发/生产/测试）：

```python
from database import get_config

# 获取不同环境配置
dev_config = get_config("dev")
prod_config = get_config("prod")
test_config = get_config("test")
```

### 连接池配置

```python
config = DatabaseConfig(
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="nju_recruitment",
    max_connections=20  # 最大连接数
)
```

## 🔍 调试和日志

模块内置日志功能，可通过以下方式查看数据库操作日志：

```python
import logging
logging.basicConfig(level=logging.INFO)

# 数据库操作将自动记录日志
student_dao.create_student(student)
# 输出: INFO:database.db_utils:成功批量插入 1 条学生记录
```

## 🚨 注意事项

1. **密码安全**: 生产环境请修改默认管理员密码
2. **数据备份**: 定期备份重要数据
3. **权限控制**: 确保数据库用户权限合理配置
4. **字符编码**: 统一使用 UTF-8 编码
5. **连接管理**: 使用连接池避免连接泄露

## 🆘 故障排除

### 常见问题

1. **连接失败**
   - 检查MySQL服务状态
   - 验证连接参数
   - 确认用户权限

2. **中文乱码**
   - 确保数据库字符集为 utf8mb4
   - 检查连接字符集配置

3. **导入错误**
   - 确保安装了 PyMySQL
   - 检查Python路径配置

### 支持联系

如遇问题请检查：
- 数据库连接配置
- MySQL服务状态  
- Python依赖安装情况

---

**© 2024 南京大学招生助手系统 - 数据库模块** 