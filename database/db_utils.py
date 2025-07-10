"""
数据库工具函数
包含数据库连接管理、CRUD操作等功能
"""

import pymysql
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime

from .config import DEFAULT_CONFIG, DatabaseConfig
from .models import *

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DEFAULT_CONFIG
        self._test_connection()
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        try:
            connection = pymysql.connect(**self.config.get_connection_params())
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"数据库操作错误: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_sql_file(self, sql_file_path: str) -> bool:
        """执行SQL文件"""
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 分割SQL语句（基于分号）
                    sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    
                    for sql in sql_statements:
                        if sql:
                            cursor.execute(sql)
                    
                    conn.commit()
                    logger.info(f"SQL文件 {sql_file_path} 执行成功")
                    return True
        except Exception as e:
            logger.error(f"执行SQL文件失败: {e}")
            return False

class StudentDAO:
    """学生数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_student(self, student: Student) -> Optional[int]:
        """创建学生记录"""
        sql = """
        INSERT INTO students (student_id, name, high_school, category, total_score, 
                            chinese_score, math_score, overall_rank, sfp_university, 
                            tele_student, tele_parent, transferable, level, admission_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        student.student_id, student.name, student.high_school,
                        student.category, student.total_score, student.chinese_score,
                        student.math_score, student.overall_rank, student.sfp_university,
                        student.tele_student, student.tele_parent, student.transferable,
                        student.level, student.admission_status.value
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建学生记录失败: {e}")
            return None
    
    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        """根据ID获取学生信息"""
        sql = "SELECT * FROM students WHERE id = %s"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (student_id,))
                    result = cursor.fetchone()
                    return self._dict_to_student(result) if result else None
        except Exception as e:
            logger.error(f"获取学生信息失败: {e}")
            return None
    
    def get_students_by_category(self, is_science: bool) -> List[Student]:
        """根据文理科类别获取学生列表"""
        sql = "SELECT * FROM students WHERE category = %s ORDER BY overall_rank"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (is_science,))
                    results = cursor.fetchall()
                    return [self._dict_to_student(row) for row in results]
        except Exception as e:
            logger.error(f"获取学生列表失败: {e}")
            return []
    
    def get_students_by_score_range(self, min_score: float, max_score: float) -> List[Student]:
        """根据分数范围获取学生列表"""
        sql = "SELECT * FROM students WHERE total_score BETWEEN %s AND %s ORDER BY total_score DESC"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (min_score, max_score))
                    results = cursor.fetchall()
                    return [self._dict_to_student(row) for row in results]
        except Exception as e:
            logger.error(f"获取学生列表失败: {e}")
            return []
    
    def update_student(self, student: Student) -> bool:
        """更新学生信息"""
        sql = """
        UPDATE students SET name=%s, high_school=%s, category=%s, total_score=%s,
                          chinese_score=%s, math_score=%s, overall_rank=%s, sfp_university=%s,
                          tele_student=%s, tele_parent=%s, transferable=%s, level=%s,
                          admission_status=%s, updated_at=NOW()
        WHERE id=%s
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (
                        student.name, student.high_school, student.category,
                        student.total_score, student.chinese_score, student.math_score,
                        student.overall_rank, student.sfp_university, student.tele_student,
                        student.tele_parent, student.transferable, student.level,
                        student.admission_status.value, student.id
                    ))
                    conn.commit()
                    return affected_rows > 0
        except Exception as e:
            logger.error(f"更新学生信息失败: {e}")
            return False
    
    def delete_student(self, student_id: int) -> bool:
        """删除学生记录"""
        sql = "DELETE FROM students WHERE id = %s"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (student_id,))
                    conn.commit()
                    return affected_rows > 0
        except Exception as e:
            logger.error(f"删除学生记录失败: {e}")
            return False
    
    def get_student_with_majors(self, student_id: int) -> Optional[Student]:
        """获取学生信息（包含意向专业和承诺专业）"""
        student = self.get_student_by_id(student_id)
        if not student:
            return None
        
        # 获取意向专业
        intended_sql = """
        SELECT major_name, priority 
        FROM student_intended_majors 
        WHERE student_id = %s 
        ORDER BY priority
        """
        
        # 获取承诺专业
        promise_sql = """
        SELECT major_name, priority 
        FROM student_promise_majors 
        WHERE student_id = %s 
        ORDER BY priority
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    # 获取意向专业
                    cursor.execute(intended_sql, (student_id,))
                    intended_results = cursor.fetchall()
                    student.intended_majors = [row['major_name'] for row in intended_results]
                    
                    # 获取承诺专业
                    cursor.execute(promise_sql, (student_id,))
                    promise_results = cursor.fetchall()
                    student.promise_majors = [row['major_name'] for row in promise_results]
                    
            return student
        except Exception as e:
            logger.error(f"获取学生完整信息失败: {e}")
            return student
    
    def batch_insert_students(self, students: List[Student]) -> bool:
        """批量插入学生数据"""
        sql = """
        INSERT INTO students (student_id, name, high_school, category, total_score, 
                            chinese_score, math_score, overall_rank, sfp_university, 
                            tele_student, tele_parent, transferable, level, admission_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    data = [
                        (s.student_id, s.name, s.high_school, s.category,
                         s.total_score, s.chinese_score, s.math_score, s.overall_rank,
                         s.sfp_university, s.tele_student, s.tele_parent,
                         s.transferable, s.level, s.admission_status.value)
                        for s in students
                    ]
                    cursor.executemany(sql, data)
                    conn.commit()
                    logger.info(f"成功批量插入 {len(students)} 条学生记录")
                    return True
        except Exception as e:
            logger.error(f"批量插入学生数据失败: {e}")
            return False
    
    def _dict_to_student(self, data: Dict[str, Any]) -> Student:
        """将字典转换为Student对象"""
        return Student(
            id=data['id'],
            student_id=data['student_id'],
            name=data['name'],
            high_school=data['high_school'],
            category=bool(data['category']),  # 转换为bool类型
            total_score=float(data['total_score']),
            chinese_score=float(data['chinese_score']),
            math_score=float(data['math_score']),
            overall_rank=data['overall_rank'],
            sfp_university=data['sfp_university'],
            tele_student=data['tele_student'],
            tele_parent=data['tele_parent'],
            transferable=data['transferable'],
            level=data['level'],
            admission_status=AdmissionStatusEnum(data['admission_status']),
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )

class CrewBaseDAO:
    """工作人员基础数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_crew_base(self, crew_base: CrewBase) -> Optional[int]:
        """创建工作人员基础记录"""
        sql = """
        INSERT INTO crew_base (name, account, password, email, color, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        crew_base.name, crew_base.account, crew_base.password,
                        crew_base.email, crew_base.color, crew_base.is_active
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建工作人员基础记录失败: {e}")
            return None
    
    def get_crew_base_by_id(self, crew_base_id: int) -> Optional[CrewBase]:
        """根据ID获取工作人员基础信息"""
        sql = "SELECT * FROM crew_base WHERE id = %s"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (crew_base_id,))
                    result = cursor.fetchone()
                    return self._dict_to_crew_base(result) if result else None
        except Exception as e:
            logger.error(f"获取工作人员基础信息失败: {e}")
            return None
    
    def get_crew_base_by_account(self, account: str) -> Optional[CrewBase]:
        """根据账号获取工作人员基础信息"""
        sql = "SELECT * FROM crew_base WHERE account = %s"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (account,))
                    result = cursor.fetchone()
                    return self._dict_to_crew_base(result) if result else None
        except Exception as e:
            logger.error(f"获取工作人员基础信息失败: {e}")
            return None
    
    def _dict_to_crew_base(self, data: Dict[str, Any]) -> CrewBase:
        """将字典转换为CrewBase对象"""
        return CrewBase(
            id=data['id'],
            name=data['name'],
            account=data['account'],
            password=data['password'],
            email=data['email'],
            color=data['color'],
            is_active=data['is_active'],
            last_login=data['last_login'],
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )

class CrewWorkFileDAO:
    """工作文件数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_work_file(self, work_file: CrewWorkFile) -> Optional[int]:
        """创建工作文件记录"""
        sql = """
        INSERT INTO crew_work_files (crew_base_id, file_name, file_original_name, 
                                   file_path, file_url, file_size, file_type, mime_type,
                                   description, access_permission, is_viewable_online)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (
                        work_file.crew_base_id, work_file.file_name, work_file.file_original_name,
                        work_file.file_path, work_file.file_url, work_file.file_size,
                        work_file.file_type, work_file.mime_type, work_file.description,
                        work_file.access_permission.value, work_file.is_viewable_online
                    ))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建工作文件记录失败: {e}")
            return None
    
    def get_files_by_crew(self, crew_base_id: int) -> List[CrewWorkFile]:
        """获取指定工作人员的文件列表"""
        sql = "SELECT * FROM crew_work_files WHERE crew_base_id = %s ORDER BY upload_time DESC"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (crew_base_id,))
                    results = cursor.fetchall()
                    return [self._dict_to_work_file(row) for row in results]
        except Exception as e:
            logger.error(f"获取工作文件列表失败: {e}")
            return []
    
    def update_file_access(self, file_id: int) -> bool:
        """更新文件访问次数和最后访问时间"""
        sql = """
        UPDATE crew_work_files 
        SET download_count = download_count + 1, last_accessed = NOW()
        WHERE id = %s
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, (file_id,))
                    conn.commit()
                    return affected_rows > 0
        except Exception as e:
            logger.error(f"更新文件访问记录失败: {e}")
            return False
    
    def _dict_to_work_file(self, data: Dict[str, Any]) -> CrewWorkFile:
        """将字典转换为CrewWorkFile对象"""
        return CrewWorkFile(
            id=data['id'],
            crew_base_id=data['crew_base_id'],
            file_name=data['file_name'],
            file_original_name=data['file_original_name'],
            file_path=data['file_path'],
            file_url=data['file_url'],
            file_size=data['file_size'],
            file_type=data['file_type'],
            mime_type=data['mime_type'],
            description=data['description'],
            access_permission=AccessPermissionEnum(data['access_permission']),
            is_viewable_online=data['is_viewable_online'],
            download_count=data['download_count'],
            last_accessed=data['last_accessed'],
            upload_time=data['upload_time']
        )

class MajorDAO:
    """专业数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_all_majors(self, is_active: bool = True) -> List[Major]:
        """获取所有专业列表"""
        sql = "SELECT * FROM majors WHERE is_active = %s ORDER BY category, major_code"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (is_active,))
                    results = cursor.fetchall()
                    return [self._dict_to_major(row) for row in results]
        except Exception as e:
            logger.error(f"获取专业列表失败: {e}")
            return []
    
    def get_majors_by_category(self, category: str) -> List[Major]:
        """根据类别获取专业列表"""
        sql = "SELECT * FROM majors WHERE category = %s AND is_active = TRUE ORDER BY major_code"
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, (category,))
                    results = cursor.fetchall()
                    return [self._dict_to_major(row) for row in results]
        except Exception as e:
            logger.error(f"获取专业列表失败: {e}")
            return []
    
    def _dict_to_major(self, data: Dict[str, Any]) -> Major:
        """将字典转换为Major对象"""
        return Major(
            id=data['id'],
            major_code=data['major_code'],
            major_name=data['major_name'],
            category=data['category'],
            quota=data['quota'],
            description=data['description'],
            is_active=data['is_active'],
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )

# 全局数据库管理器实例
db_manager = DatabaseManager()
student_dao = StudentDAO(db_manager)
crew_base_dao = CrewBaseDAO(db_manager)
crew_work_file_dao = CrewWorkFileDAO(db_manager)
major_dao = MajorDAO(db_manager)

# 便捷函数
def init_database(sql_file_path: str = "database/create_tables.sql") -> bool:
    """初始化数据库"""
    return db_manager.execute_sql_file(sql_file_path)

def get_student_dao() -> StudentDAO:
    """获取学生DAO实例"""
    return student_dao

def get_crew_base_dao() -> CrewBaseDAO:
    """获取工作人员基础DAO实例"""
    return crew_base_dao

def get_crew_work_file_dao() -> CrewWorkFileDAO:
    """获取工作文件DAO实例"""
    return crew_work_file_dao

def get_major_dao() -> MajorDAO:
    """获取专业DAO实例"""
    return major_dao 