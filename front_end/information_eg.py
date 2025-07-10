


class Student:
    def __init__(self,name:str,high_school:str,category:bool,total_score:float,chinese_score:float,math_score:float,overall_rank:int,sfp_university:str,tele_student:str,tele_parent:str,due_charger:list,intended_majors:list,transferable:bool,record:{},level:int,promise:list):
        #考生姓名
        self.name = name

        #考生高中学校名
        self.high_school = high_school

        #考生是文科生还是理科生
        self.category = category

        #考生高考总分
        self.total_score = total_score

        #考试高考语文分数
        self.chinese_score = chinese_score

        #考生高考数学分数
        self.math_score = math_score

        #考生省排名
        self.overall_rank = overall_rank

        #考试强基学校（如果没有就是空字符串）
        self.sfp_university = sfp_university if sfp_university else ''

        #考生自己联系电话
        self.tele_student = tele_student.strip()

        #考生家长联系电话
        self.tele_parent = tele_parent.strip()

        #考生负责人
        self.due_charger = due_charger

        #考生意向专业（可以为空），为专业名（字符串）组成的列表
        self.intended_majors = intended_majors if intended_majors else []

        #考生是否服从调剂（可以为空）
        self.transferable = transferable

        #考生沟通记录（可以为空），为[联系时间时间,联系人]->沟通内容摘要
        self.record = record if record else {}

        #考生意向等级，0-100分
        self.level = level

        #招生组对考生的承诺专业，为专业名（字符串）组成的列表
        self.promise = promise if promise else []






class crew():
    def __init__(self,name:str,account:str,password:str,worklist:list,work_files:list,email:str) :
        #工作人员名字
        self.name = name
        #工作人员账号
        self.account = account
        #账号密码
        self.password = password
        #工作人员需要联系的学生，工作人员随时自己通过网页维护，由考生名字（字符串）组成的列表。
        self.worklist = worklist if worklist else []
        #工作人员工作时需要查看的文件，具体实现方式我不清楚
        self.work_files = work_files if work_files else []
        #工作人员邮箱
        self.email = email



class crew_member(crew):
    def __init__(self, name: str, account: str, password: str, worklist: list, work_files: list, email: str,color: str):
        #同crew
        super().__init__(name, account, password, worklist, work_files, email)



class crew_leader(crew):
    def __init__(self, name: str, account: str, password: str, worklist: list, work_files: list, email: str,color: str):
        #同crew
        super().__init__(name, account, password, worklist, work_files, email)

