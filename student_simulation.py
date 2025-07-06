from dataclasses import dataclass
from typing import List, Optional
import json
import pandas as pd


@dataclass
class Student:
    """学生信息类，用于模拟报考"""
    name: str              # 姓名
    rank: str              # 位次
    intended_majors: str   # 意向专业
    promised_major: str    # 承诺专业
    subject_type: str      # 专业类别（理科/文科）
    total_score: str       # 总分
    math_score: str = ""   # 数学分数
    chinese_score: str = "" # 语文分数
    accepts_transfer: bool = False  # 是否服从调剂

    @property
    def total_score_int(self) -> int:
        """获取总分的整数值"""
        try:
            return int(self.total_score)
        except ValueError:
            return 0

    @property
    def rank_int(self) -> int:
        """获取排名的整数值"""
        try:
            return int(self.rank)
        except ValueError:
            return 999999

    @property
    def math_score_int(self) -> int:
        """获取数学分数的整数值"""
        try:
            return int(self.math_score) if self.math_score else 0
        except ValueError:
            return 0

    @property
    def chinese_score_int(self) -> int:
        """获取语文分数的整数值"""
        try:
            return int(self.chinese_score) if self.chinese_score else 0
        except ValueError:
            return 0

    @property
    def math_chinese_sum(self) -> int:
        """获取数学+语文总分"""
        return self.math_score_int + self.chinese_score_int

    @property
    def math_chinese_max(self) -> int:
        """获取数学和语文中的最高分"""
        return max(self.math_score_int, self.chinese_score_int)

    def get_intended_majors_list(self) -> List[str]:
        """解析意向专业字符串，返回专业列表"""
        if not self.intended_majors:
            return []
        
        # 按行分割，去除空行和编号
        lines = [line.strip() for line in self.intended_majors.split('\n') if line.strip()]
        major_list = []
        
        for line in lines:
            # 处理不同的编号格式
            if '. ' in line:
                # 格式: "1. 003" 或 "1-1. 专业名称"
                major = line.split('. ', 1)[-1].strip()
                # 过滤掉纯数字代码（如"003"），只保留真正的专业名称
                if major and not major.isdigit():
                    major_list.append(major)
            elif '-' in line and line.count('-') >= 3:
                # 格式: "1-001-1-专业名称"
                parts = line.split('-')
                if len(parts) >= 4:
                    major = '-'.join(parts[3:]).strip()  # 取第4部分及之后作为专业名称
                    if major:
                        major_list.append(major)
            elif line and not line[0].isdigit():
                major_list.append(line)
        
        return major_list

    def get_promised_major_list(self) -> List[str]:
        """解析承诺专业字符串，返回专业列表"""
        if not self.promised_major:
            return []
        
        # 按行分割，去除空行和编号
        lines = [line.strip() for line in self.promised_major.split('\n') if line.strip()]
        major_list = []
        
        for line in lines:
            # 处理不同的编号格式
            if '. ' in line:
                # 格式: "1. 003" 或 "1-1. 专业名称"
                major = line.split('. ', 1)[-1].strip()
                # 过滤掉纯数字代码（如"003"），只保留真正的专业名称
                if major and not major.isdigit():
                    major_list.append(major)
            elif '-' in line and line.count('-') >= 3:
                # 格式: "1-001-1-专业名称"
                parts = line.split('-')
                if len(parts) >= 4:
                    major = '-'.join(parts[3:]).strip()  # 取第4部分及之后作为专业名称
                    if major:
                        major_list.append(major)
            elif line and not line[0].isdigit():
                major_list.append(line)
        
        return major_list

    def is_high_score_student(self, score_threshold: int = 650) -> bool:
        """判断是否为高分考生"""
        return self.total_score_int >= score_threshold

    def is_top_rank_student(self, rank_threshold: int = 200) -> bool:
        """判断是否为高排名考生"""
        return self.rank_int <= rank_threshold

    def __str__(self) -> str:
        return f"学生：{self.name}（{self.subject_type}）- 总分：{self.total_score}，排名：{self.rank}"


class StudentDatabase:
    """学生数据库类，用于管理学生信息"""
    
    def __init__(self):
        self.students: List[Student] = []
    
    def _parse_transfer_acceptance(self, transfer_str: str) -> bool:
        """解析是否调剂字段，返回布尔值"""
        if not transfer_str:
            return False
        
        transfer_str = str(transfer_str).strip()
        # 处理各种可能的表示方式 - 不要转换为小写，保持中文字符原样
        positive_indicators = ['是', 'YES', 'yes', 'Y', 'y', '服从', '同意', '接受', '1', 'true', 'TRUE']
        negative_indicators = ['否', 'NO', 'no', 'N', 'n', '不服从', '不同意', '不接受', '0', 'false', 'FALSE']
        
        # 直接匹配，优先检查否定指示符
        for neg in negative_indicators:
            if neg in transfer_str:
                return False
        
        # 再检查肯定指示符
        for pos in positive_indicators:
            if pos in transfer_str:
                return True
                
        return False

    def load_from_json(self, file_path: str) -> None:
        """从JSON文件加载学生信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.students = []
            for student_data in data:
                # 只提取核心字段
                student = Student(
                    name=student_data.get("姓名", ""),
                    rank=student_data.get("排名", ""),
                    intended_majors=student_data.get("意向专业", ""),
                    promised_major=student_data.get("承诺专业", ""),
                    subject_type=student_data.get("专业类别", ""),
                    total_score=student_data.get("总分", ""),
                    math_score=student_data.get("数学分数", ""),
                    chinese_score=student_data.get("语文分数", ""),
                    accepts_transfer=self._parse_transfer_acceptance(student_data.get("是否调剂", ""))
                )
                self.students.append(student)
            
            print(f"成功加载 {len(self.students)} 名学生信息")
        
        except FileNotFoundError:
            print(f"文件 {file_path} 不存在")
        except Exception as e:
            print(f"加载学生信息时发生错误：{e}")

    def load_from_xlsx(self, file_path: str) -> None:
        """从Excel文件加载学生信息"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            self.students = []
            for _, row in df.iterrows():
                # 处理缺失值，将NaN转换为空字符串
                student = Student(
                    name=str(row.get("姓名", "")) if pd.notna(row.get("姓名")) else "",
                    rank=str(row.get("排名", "")) if pd.notna(row.get("排名")) else "",
                    intended_majors=str(row.get("意向专业", "")) if pd.notna(row.get("意向专业")) else "",
                    promised_major=str(row.get("承诺专业", "")) if pd.notna(row.get("承诺专业")) else "",
                    subject_type=str(row.get("专业类别", "")) if pd.notna(row.get("专业类别")) else "",
                    total_score=str(row.get("总分", "")) if pd.notna(row.get("总分")) else "",
                    math_score=str(row.get("数学分数", "")) if pd.notna(row.get("数学分数")) else "",
                    chinese_score=str(row.get("语文分数", "")) if pd.notna(row.get("语文分数")) else "",
                    accepts_transfer=self._parse_transfer_acceptance(str(row.get("是否服从调剂", "")) if pd.notna(row.get("是否服从调剂")) else "")
                )
                self.students.append(student)
            
            print(f"成功从Excel文件加载 {len(self.students)} 名学生信息")
        
        except FileNotFoundError:
            print(f"文件 {file_path} 不存在")
        except Exception as e:
            print(f"加载Excel文件时发生错误：{e}")

    def add_student(self, student: Student) -> None:
        """添加学生"""
        self.students.append(student)

    def get_student_by_name(self, name: str) -> Optional[Student]:
        """根据姓名查找学生"""
        for student in self.students:
            if student.name == name:
                return student
        return None

    def get_students_by_score_range(self, min_score: int, max_score: int) -> List[Student]:
        """根据分数范围筛选学生"""
        return [s for s in self.students if min_score <= s.total_score_int <= max_score]

    def get_students_by_rank_range(self, min_rank: int, max_rank: int) -> List[Student]:
        """根据排名范围筛选学生"""
        return [s for s in self.students if min_rank <= s.rank_int <= max_rank]

    def get_students_by_subject_type(self, subject_type: str) -> List[Student]:
        """根据专业类别筛选学生"""
        return [s for s in self.students if s.subject_type == subject_type]

    def print_summary(self) -> None:
        """打印学生信息摘要"""
        if not self.students:
            print("暂无学生信息")
            return

        print(f"\n=== 学生信息摘要 ===")
        print(f"总学生数：{len(self.students)}")
        
        # 按专业类别统计
        science_count = len([s for s in self.students if s.subject_type == "理科"])
        liberal_arts_count = len([s for s in self.students if s.subject_type == "文科"])
        print(f"理科生：{science_count} 人，文科生：{liberal_arts_count} 人")
        
        # 分数统计
        scores = [s.total_score_int for s in self.students if s.total_score_int > 0]
        if scores:
            print(f"分数范围：{min(scores)} - {max(scores)}")
            print(f"平均分：{sum(scores) / len(scores):.1f}")

        # 位次统计
        ranks = [s.rank_int for s in self.students if s.rank_int < 999999]
        if ranks:
            print(f"位次范围：{min(ranks)} - {max(ranks)}")

    def __len__(self) -> int:
        return len(self.students)

    def __iter__(self):
        return iter(self.students)


def evaluate_simulation_result(major_counter: dict, unsatisfied: list, slide: list, total_students: int) -> dict:
    """
    评估模拟结果的质量
    
    Args:
        major_counter: 各专业录取的学生列表
        unsatisfied: 未满足承诺专业的学生列表
        slide: 滑档学生列表
        total_students: 总学生数
    
    Returns:
        评估指标字典
    """
    total_admitted = sum(len(students) for students in major_counter.values())
    
    evaluation = {
        'total_admitted': total_admitted,
        'unsatisfied_count': len(unsatisfied),
        'slide_count': len(slide),
        'admission_rate': total_admitted / total_students if total_students > 0 else 0,
        'satisfaction_rate': (total_students - len(unsatisfied) - len(slide)) / total_students if total_students > 0 else 0,
        # 综合评分：录取人数最大化，滑档和未满足承诺最小化
        'score': total_admitted * 1000 - len(slide) * 10 - len(unsatisfied) * 100
    }
    
    return evaluation


def generate_quota_allocations(original_plan: dict, reducible_majors: list, max_reduction: dict = None) -> list:
    """
    生成所有可能的名额分配方案
    
    Args:
        original_plan: 原始招生计划 {'专业名': 名额数}
        reducible_majors: 可以减少名额的专业列表
        max_reduction: 每个专业最大可减少的名额数 {'专业名': 最大减少数}，如果None则最多减到1
    
    Returns:
        所有可能的分配方案列表
    """
    if max_reduction is None:
        # 默认每个专业最多减少到剩余1个名额
        max_reduction = {major: max(0, original_plan[major] - 1) for major in reducible_majors}
    
    # 获取可增加名额的专业（非减少专业）
    increasable_majors = [major for major in original_plan.keys() if major not in reducible_majors]
    
    allocations = []
    
    # 生成所有可能的减少组合
    from itertools import product
    
    # 每个可减少专业的减少范围
    reduction_ranges = []
    for major in reducible_majors:
        max_reduce = min(max_reduction.get(major, 0), original_plan[major] - 1)
        reduction_ranges.append(range(max_reduce + 1))  # 0到max_reduce的所有可能
    
    # 生成所有减少组合
    for reduction_combination in product(*reduction_ranges):
        total_reduced = sum(reduction_combination)
        
        if total_reduced == 0:
            # 没有减少名额，保持原方案
            allocations.append(original_plan.copy())
            continue
        
        # 将减少的名额分配给可增加的专业
        # 生成所有可能的增加分配
        for increase_allocation in _generate_increase_allocations(increasable_majors, total_reduced):
            new_plan = original_plan.copy()
            
            # 应用减少
            for i, major in enumerate(reducible_majors):
                new_plan[major] -= reduction_combination[i]
            
            # 应用增加
            for major, increase in increase_allocation.items():
                new_plan[major] += increase
            
            allocations.append(new_plan)
    
    return allocations


def generate_adjustment_schemes(original_plan: dict, major_counter: dict, 
                              reducible_majors: dict, increasable_majors: list) -> list:
    """
    生成所有可能的名额调整方案
    
    Args:
        original_plan: 原始招生计划 {'专业名': 名额数}
        major_counter: 当前录取结果 {'专业名': [学生列表]}
        reducible_majors: 可减专业及其空余名额 {'专业名': 空余数}
        increasable_majors: 可增加名额的专业列表
    
    Returns:
        所有可能的调整方案列表
    """
    if not reducible_majors or not increasable_majors:
        return [original_plan.copy()]
    
    # 计算总的可调整名额数
    total_reducible_quota = sum(reducible_majors.values())
    
    # 生成所有可能的减少组合
    from itertools import product
    
    # 每个可减专业的减少范围（0到其空余名额数）
    reduction_ranges = []
    reducible_major_names = list(reducible_majors.keys())
    
    for major in reducible_major_names:
        max_reduce = reducible_majors[major]  # 最多减少其空余名额数
        reduction_ranges.append(range(max_reduce + 1))  # 0到max_reduce的所有可能
    
    adjustment_schemes = []
    
    # 生成所有减少组合
    for reduction_combination in product(*reduction_ranges):
        total_reduced = sum(reduction_combination)
        
        if total_reduced == 0:
            # 没有减少名额，保持原方案
            continue
        
        # 将减少的名额分配给可增加的专业
        for increase_allocation in _generate_increase_allocations(increasable_majors, total_reduced):
            new_plan = original_plan.copy()
            
            # 应用减少（从原计划中减去空余名额）
            for i, major in enumerate(reducible_major_names):
                new_plan[major] -= reduction_combination[i]
            
            # 应用增加
            for major, increase in increase_allocation.items():
                new_plan[major] += increase
            
            adjustment_schemes.append(new_plan)
    
    return adjustment_schemes


def _generate_increase_allocations(increasable_majors: list, total_quota: int) -> list:
    """
    生成将total_quota个名额分配给increasable_majors的所有可能方案
    """
    if not increasable_majors or total_quota <= 0:
        return [{}]
    
    if len(increasable_majors) == 1:
        return [{increasable_majors[0]: total_quota}]
    
    allocations = []
    first_major = increasable_majors[0]
    remaining_majors = increasable_majors[1:]
    
    # 给第一个专业分配0到total_quota个名额
    for allocation_to_first in range(total_quota + 1):
        remaining_quota = total_quota - allocation_to_first
        
        # 递归分配剩余名额
        for sub_allocation in _generate_increase_allocations(remaining_majors, remaining_quota):
            allocation = {first_major: allocation_to_first}
            allocation.update(sub_allocation)
            allocations.append(allocation)
    
    return allocations


def optimize_quota_allocation(students: list, original_plan: dict, reducible_majors: list, 
                            max_reduction: dict = None, top_k: int = 5) -> dict:
    """
    全搜索优化名额分配方案
    
    Args:
        students: 学生列表
        original_plan: 原始招生计划
        reducible_majors: 可以减少名额的专业列表
        max_reduction: 每个专业最大可减少的名额数
        top_k: 返回前k个最优方案
    
    Returns:
        优化结果字典，包含最优方案和所有方案的评估结果
    """
    print(f"开始全搜索名额分配优化...")
    print(f"原始计划: {original_plan}")
    print(f"可减少专业: {reducible_majors}")
    
    # 生成所有可能的分配方案
    all_allocations = generate_quota_allocations(original_plan, reducible_majors, max_reduction)
    print(f"生成了 {len(all_allocations)} 种分配方案")
    
    results = []
    
    # 对每种方案进行模拟
    for i, allocation in enumerate(all_allocations):
        if i % 10 == 0:
            print(f"正在模拟第 {i+1}/{len(all_allocations)} 种方案...")
        
        try:
            major_counter, unsatisfied, slide = simulate_major_assignment(students, allocation)
            evaluation = evaluate_simulation_result(major_counter, unsatisfied, slide, len(students))
            
            result = {
                'allocation': allocation,
                'major_counter': major_counter,
                'unsatisfied': unsatisfied,
                'slide': slide,
                'evaluation': evaluation
            }
            results.append(result)
            
        except Exception as e:
            print(f"方案 {i+1} 模拟失败: {e}")
            continue
    
    # 按评分排序，找到最优方案
    results.sort(key=lambda x: x['evaluation']['score'], reverse=True)
    
    print(f"优化完成！找到 {len(results)} 个有效方案")
    
    return {
        'best_result': results[0] if results else None,
        'top_results': results[:top_k],
        'all_results': results,
        'original_plan': original_plan,
        'total_allocations_tested': len(all_allocations)
    }


def calculate_comprehensive_metrics(major_counter: dict, unsatisfied: list, slide: list, 
                                  allocation: dict, original_plan: dict) -> dict:
    """
    计算更全面的评估指标
    
    Args:
        major_counter: 各专业录取的学生列表
        unsatisfied: 未满足承诺专业的学生列表
        slide: 滑档学生列表
        allocation: 当前名额分配方案
        original_plan: 原始名额分配方案
    
    Returns:
        comprehensive_metrics: 综合评估指标字典
    """
    total_students = len(unsatisfied) + len(slide) + sum(len(students) for students in major_counter.values())
    total_admitted = sum(len(students) for students in major_counter.values())
    total_quota = sum(allocation.values())
    
    # 基础指标
    basic_metrics = {
        'total_admitted': total_admitted,
        'unsatisfied_count': len(unsatisfied),
        'slide_count': len(slide),
        'admission_rate': total_admitted / total_students if total_students > 0 else 0,
        'quota_utilization': total_admitted / total_quota if total_quota > 0 else 0,
    }
    
    # 专业平衡性指标
    filled_majors = sum(1 for students in major_counter.values() if len(students) > 0)
    total_majors = len(allocation)
    major_balance = filled_majors / total_majors if total_majors > 0 else 0
    
    # 名额变化指标
    quota_changes = {}
    total_increase = 0
    total_decrease = 0
    changed_majors = 0
    
    for major in allocation:
        change = allocation[major] - original_plan[major]
        quota_changes[major] = change
        if change > 0:
            total_increase += change
        elif change < 0:
            total_decrease += abs(change)
        if change != 0:
            changed_majors += 1
    
    stability_score = (total_majors - changed_majors) / total_majors if total_majors > 0 else 1
    
    # 专业满额情况
    fully_filled = sum(1 for major, students in major_counter.items() if len(students) == allocation[major])
    fill_rate_score = fully_filled / total_majors if total_majors > 0 else 0
    
    # 分数分布指标（录取学生的分数分布）
    all_admitted_scores = []
    for students in major_counter.values():
        for student in students:
            all_admitted_scores.append(student.total_score_int)
    
    score_metrics = {}
    if all_admitted_scores:
        all_admitted_scores.sort(reverse=True)
        score_metrics = {
            'highest_score': all_admitted_scores[0],
            'lowest_score': all_admitted_scores[-1],
            'score_range': all_admitted_scores[0] - all_admitted_scores[-1],
            'median_score': all_admitted_scores[len(all_admitted_scores)//2]
        }
    
    # 综合评分 - 可以根据不同权重调整
    comprehensive_score = (
        total_admitted * 100 +          # 录取人数权重
        (1 - len(slide)/total_students) * 50 +  # 减少滑档权重
        major_balance * 30 +            # 专业平衡权重
        stability_score * 20 +          # 方案稳定性权重
        fill_rate_score * 15            # 专业满额率权重
    )
    
    return {
        **basic_metrics,
        'major_balance_score': major_balance,
        'stability_score': stability_score,
        'fill_rate_score': fill_rate_score,
        'quota_changes': quota_changes,
        'total_quota_increase': total_increase,
        'total_quota_decrease': total_decrease,
        'changed_majors_count': changed_majors,
        'filled_majors_count': filled_majors,
        'comprehensive_score': comprehensive_score,
        **score_metrics
    }


def comprehensive_quota_analysis(students: list, original_plan: dict, reducible_majors: list, 
                               max_reduction: dict = None) -> dict:
    """
    全面的名额分配分析，保存所有可能的方案及其详细评估
    
    Args:
        students: 学生列表
        original_plan: 原始招生计划
        reducible_majors: 可以减少名额的专业列表
        max_reduction: 每个专业最大可减少的名额数
    
    Returns:
        完整的分析结果，包含所有方案的详细信息
    """
    print(f"开始全面名额分配分析...")
    print(f"原始计划: {original_plan}")
    print(f"可减少专业: {reducible_majors}")
    
    # 生成所有可能的分配方案
    all_allocations = generate_quota_allocations(original_plan, reducible_majors, max_reduction)
    print(f"生成了 {len(all_allocations)} 种分配方案")
    
    comprehensive_results = []
    
    # 对每种方案进行详细分析
    for i, allocation in enumerate(all_allocations):
        if i % 20 == 0:
            print(f"正在分析第 {i+1}/{len(all_allocations)} 种方案...")
        
        try:
            major_counter, unsatisfied, slide = simulate_major_assignment(students, allocation)
            
            # 计算综合指标
            comprehensive_metrics = calculate_comprehensive_metrics(
                major_counter, unsatisfied, slide, allocation, original_plan
            )
            
            result = {
                'scheme_id': i + 1,
                'allocation': allocation,
                'major_counter': major_counter,
                'unsatisfied': unsatisfied,
                'slide': slide,
                'metrics': comprehensive_metrics
            }
            comprehensive_results.append(result)
            
        except Exception as e:
            print(f"方案 {i+1} 分析失败: {e}")
            continue
    
    print(f"分析完成！成功分析了 {len(comprehensive_results)} 个方案")
    
    return {
        'all_schemes': comprehensive_results,
        'original_plan': original_plan,
        'analysis_summary': {
            'total_schemes': len(all_allocations),
            'valid_schemes': len(comprehensive_results),
            'students_count': len(students),
            'original_quota': sum(original_plan.values())
        }
    }


def filter_and_rank_schemes(analysis_result: dict, criteria: dict = None) -> list:
    """
    根据指定标准筛选和排序方案
    
    Args:
        analysis_result: comprehensive_quota_analysis的返回结果
        criteria: 筛选和排序标准
            {
                'min_admission_rate': 0.5,      # 最低录取率
                'max_slide_count': 10,          # 最大滑档数
                'min_stability_score': 0.8,     # 最低稳定性评分
                'min_major_balance': 0.7,       # 最低专业平衡性
                'sort_by': 'comprehensive_score', # 排序依据
                'sort_desc': True               # 降序排列
            }
    
    Returns:
        筛选和排序后的方案列表
    """
    if criteria is None:
        criteria = {'sort_by': 'comprehensive_score', 'sort_desc': True}
    
    schemes = analysis_result['all_schemes']
    
    # 筛选
    filtered_schemes = []
    for scheme in schemes:
        metrics = scheme['metrics']
        
        # 应用筛选条件
        if criteria.get('min_admission_rate') and metrics['admission_rate'] < criteria['min_admission_rate']:
            continue
        if criteria.get('max_slide_count') and metrics['slide_count'] > criteria['max_slide_count']:
            continue
        if criteria.get('min_stability_score') and metrics['stability_score'] < criteria['min_stability_score']:
            continue
        if criteria.get('min_major_balance') and metrics['major_balance_score'] < criteria['min_major_balance']:
            continue
        if criteria.get('max_quota_change') and metrics['total_quota_increase'] + metrics['total_quota_decrease'] > criteria['max_quota_change']:
            continue
        
        filtered_schemes.append(scheme)
    
    # 排序
    sort_key = criteria.get('sort_by', 'comprehensive_score')
    sort_desc = criteria.get('sort_desc', True)
    
    if sort_key in ['allocation', 'major_counter', 'unsatisfied', 'slide']:
        # 对于非数值字段，使用综合评分排序
        sort_key = 'comprehensive_score'
    
    try:
        filtered_schemes.sort(
            key=lambda x: x['metrics'][sort_key], 
            reverse=sort_desc
        )
    except KeyError:
        print(f"警告：排序字段 '{sort_key}' 不存在，使用综合评分排序")
        filtered_schemes.sort(
            key=lambda x: x['metrics']['comprehensive_score'], 
            reverse=True
        )
    
    return filtered_schemes


def print_comprehensive_analysis(analysis_result: dict, criteria: dict = None, 
                               top_n: int = 5, detailed: bool = False):
    """
    打印全面分析结果
    
    Args:
        analysis_result: comprehensive_quota_analysis的返回结果
        criteria: 筛选标准
        top_n: 显示前n个方案
        detailed: 是否显示详细信息
    """
    schemes = filter_and_rank_schemes(analysis_result, criteria)
    summary = analysis_result['analysis_summary']
    
    print("\n" + "="*80)
    print("📊 全面名额分配分析结果")
    print("="*80)
    
    print(f"\n📈 分析概览:")
    print(f"总方案数: {summary['total_schemes']}")
    print(f"有效方案: {summary['valid_schemes']}")
    print(f"学生总数: {summary['students_count']}")
    print(f"原始名额: {summary['original_quota']}")
    
    if criteria:
        print(f"筛选后方案: {len(schemes)}")
        print(f"筛选条件: {criteria}")
    
    if not schemes:
        print("❌ 没有符合条件的方案！")
        return
    
    print(f"\n🏆 前 {min(top_n, len(schemes))} 个推荐方案:")
    print("-" * 80)
    
    for i, scheme in enumerate(schemes[:top_n]):
        metrics = scheme['metrics']
        allocation = scheme['allocation']
        
        print(f"\n【方案 {scheme['scheme_id']}】")
        print(f"综合评分: {metrics['comprehensive_score']:.1f}")
        print(f"录取人数: {metrics['total_admitted']} | 录取率: {metrics['admission_rate']:.1%}")
        print(f"滑档人数: {metrics['slide_count']} | 未满足承诺: {metrics['unsatisfied_count']}")
        print(f"专业平衡: {metrics['major_balance_score']:.1%} | 稳定性: {metrics['stability_score']:.1%}")
        print(f"名额利用率: {metrics['quota_utilization']:.1%}")
        
        # 显示名额变化
        changes = []
        for major, change in metrics['quota_changes'].items():
            if change != 0:
                changes.append(f"{major}{change:+d}")
        if changes:
            print(f"名额调整: {', '.join(changes)}")
        else:
            print("名额调整: 无变化")
        
        if detailed:
            print(f"\n  详细名额分配:")
            for major, quota in allocation.items():
                admitted = len(scheme['major_counter'][major])
                status = "满" if admitted == quota else f"空{quota-admitted}"
                print(f"    {major}: {admitted}/{quota} ({status})")
    
    # 显示统计摘要
    if len(schemes) > 1:
        print(f"\n📊 方案统计摘要:")
        admission_rates = [s['metrics']['admission_rate'] for s in schemes]
        slide_counts = [s['metrics']['slide_count'] for s in schemes]
        stability_scores = [s['metrics']['stability_score'] for s in schemes]
        
        print(f"录取率范围: {min(admission_rates):.1%} - {max(admission_rates):.1%}")
        print(f"滑档数范围: {min(slide_counts)} - {max(slide_counts)}")
        print(f"稳定性范围: {min(stability_scores):.1%} - {max(stability_scores):.1%}")


def save_analysis_results(analysis_result: dict, filename: str = "comprehensive_analysis.json"):
    """
    保存完整分析结果到文件
    
    Args:
        analysis_result: 分析结果
        filename: 保存文件名
    """
    import json
    
    # 转换为可序列化的格式
    serializable_data = {
        'analysis_summary': analysis_result['analysis_summary'],
        'original_plan': analysis_result['original_plan'],
        'schemes': []
    }
    
    for scheme in analysis_result['all_schemes']:
        serializable_scheme = {
            'scheme_id': scheme['scheme_id'],
            'allocation': scheme['allocation'],
            'metrics': scheme['metrics'],
            'admitted_students': {
                major: [{'name': s.name, 'rank': s.rank, 'score': s.total_score} 
                       for s in students]
                for major, students in scheme['major_counter'].items()
            },
            'unsatisfied_students': [{'name': s.name, 'rank': s.rank, 'score': s.total_score} 
                                   for s in scheme['unsatisfied']],
            'slide_students': [{'name': s.name, 'rank': s.rank, 'score': s.total_score} 
                             for s in scheme['slide']]
        }
        serializable_data['schemes'].append(serializable_scheme)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 分析结果已保存到 {filename}")


def print_optimization_results(optimization_result: dict, original_result: tuple = None, detailed: bool = True):
    """
    打印优化结果
    
    Args:
        optimization_result: optimize_quota_allocation的返回结果
        original_result: 原始方案的模拟结果 (major_counter, unsatisfied, slide)
        detailed: 是否显示详细信息
    """
    if not optimization_result['best_result']:
        print("没有找到有效的分配方案！")
        return
    
    best = optimization_result['best_result']
    original_plan = optimization_result['original_plan']
    
    print("\n" + "="*70)
    print("🏆 最优名额分配方案")
    print("="*70)
    
    # 显示方案对比
    print("\n📊 名额分配对比:")
    print(f"{'专业名':<25} {'原计划':<8} {'最优方案':<8} {'变化':<8}")
    print("-" * 55)
    
    for major in original_plan.keys():
        original = original_plan[major]
        optimized = best['allocation'][major]
        change = optimized - original
        change_str = f"+{change}" if change > 0 else str(change) if change < 0 else "0"
        print(f"{major:<25} {original:<8} {optimized:<8} {change_str:<8}")
    
    # 显示结果对比
    if original_result:
        print(f"\n📈 效果对比:")
        orig_major_counter, orig_unsatisfied, orig_slide = original_result
        
        # 计算学生总数
        total_students = (len(orig_unsatisfied) + len(orig_slide) + 
                         sum(len(students) for students in orig_major_counter.values()))
        
        orig_evaluation = evaluate_simulation_result(orig_major_counter, orig_unsatisfied, orig_slide, total_students)
        best_eval = best['evaluation']
        
        print(f"{'指标':<15} {'原方案':<10} {'最优方案':<10} {'改善':<10}")
        print("-" * 50)
        print(f"{'录取人数':<15} {orig_evaluation['total_admitted']:<10} {best_eval['total_admitted']:<10} {best_eval['total_admitted'] - orig_evaluation['total_admitted']:+d}")
        print(f"{'滑档人数':<15} {orig_evaluation['slide_count']:<10} {best_eval['slide_count']:<10} {best_eval['slide_count'] - orig_evaluation['slide_count']:+d}")
        print(f"{'未满足承诺':<15} {orig_evaluation['unsatisfied_count']:<10} {best_eval['unsatisfied_count']:<10} {best_eval['unsatisfied_count'] - orig_evaluation['unsatisfied_count']:+d}")
        print(f"{'录取率':<15} {orig_evaluation['admission_rate']:.1%} {best_eval['admission_rate']:.1%} {best_eval['admission_rate'] - orig_evaluation['admission_rate']:+.1%}")
    
    if detailed:
        print(f"\n📋 最优方案详细录取情况:")
        for major, students in best['major_counter'].items():
            print(f"\n【{major}】- 录取 {len(students)} 名")
            if students:
                for i, student in enumerate(students[:3]):  # 只显示前3名
                    print(f"  {i+1}. {student.name} (排名{student.rank})")
                if len(students) > 3:
                    print(f"  ... 还有 {len(students) - 3} 名学生")
    
    # 显示前几个最优方案
    print(f"\n🎯 前 {len(optimization_result['top_results'])} 个最优方案评分:")
    for i, result in enumerate(optimization_result['top_results']):
        score = result['evaluation']['score']
        admitted = result['evaluation']['total_admitted']
        slide = result['evaluation']['slide_count']
        print(f"  方案{i+1}: 评分{score} (录取{admitted}人, 滑档{slide}人)")


def bubble_sort_students(students: List[Student]) -> List[Student]:
    """
    冒泡排序：按位次优先，同位次时按数学+语文总分，再按数学语文最高分排序
    
    排序逻辑：
    1. 位次从小到大（位次越小排名越靠前）
    2. 位次相同时，数学+语文总分从大到小
    3. 数学+语文总分也相同时，数学和语文最高分从大到小
    """
    if not students:
        return []
    
    # 创建副本避免修改原列表
    sorted_students = students.copy()
    n = len(sorted_students)
    
    for i in range(n):
        for j in range(0, n - i - 1):
            student1 = sorted_students[j]
            student2 = sorted_students[j + 1]
            
            # 比较逻辑
            should_swap = False
            
            # 1. 首先比较位次（位次小的排在前面）
            if student1.rank_int > student2.rank_int:
                should_swap = True
            elif student1.rank_int == student2.rank_int:
                # 2. 位次相同，比较数学+语文总分（分数高的排在前面）
                if student1.math_chinese_sum < student2.math_chinese_sum:
                    should_swap = True
                elif student1.math_chinese_sum == student2.math_chinese_sum:
                    # 3. 数学+语文总分也相同，比较数学语文最高分（分数高的排在前面）
                    if student1.math_chinese_max < student2.math_chinese_max:
                        should_swap = True
            
            if should_swap:
                sorted_students[j], sorted_students[j + 1] = sorted_students[j + 1], sorted_students[j]
    
    return sorted_students


def simulate_major_assignment_with_transfer(s_list: List[Student], available_majors: dict) -> List[dict]:
    """
    模拟专业分配算法（包含调剂逻辑）
    
    Args:
        s_list: 学生列表
        available_majors: 可用专业字典，格式为 {'专业名称': 录取名额}
    
    Returns:
        List[dict]: 所有可能的基础分配方案，每个方案包含:
        - major_counter: 各专业录取的学生列表
        - unsatisfied: 不能满足承诺专业从而没有去向的学生列表
        - slide: 没有保专业但录取滑档的学生列表
        - transfer_assignments: 调剂分配的学生列表
    """
    
    # 使用冒泡排序：按位次优先，同位次时比较数学+语文分数
    sorted_students = bubble_sort_students(s_list)
    
    # 计算总计划数
    total_quota = sum(available_majors.values())
    
    # 只取前总计划数个学生进行模拟
    if len(sorted_students) > total_quota:
        sorted_students = sorted_students[:total_quota]
        print(f"学生总数({len(s_list)})超过计划总数({total_quota})，只考虑前{total_quota}个学生进行模拟")
    
    def simulate_recursive(student_index: int, major_counter: dict, unsatisfied: list, slide: list, transfer_assignments: list) -> List[dict]:
        """递归模拟分配，处理调剂分支"""
        if student_index >= len(sorted_students):
            # 所有学生都已处理完毕，返回当前方案
            return [{
                'major_counter': {k: v.copy() for k, v in major_counter.items()},
                'unsatisfied': unsatisfied.copy(),
                'slide': slide.copy(),
                'transfer_assignments': transfer_assignments.copy()
            }]
        
        student = sorted_students[student_index]
        all_schemes = []
        
        promised_list = student.get_promised_major_list()
        
        if promised_list:
            # 有承诺专业的学生，优先按承诺专业分配
            assigned = False
            for major in promised_list:
                if major in available_majors and available_majors[major] > len(major_counter[major]):
                    new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                    new_major_counter[major].append(student)
                    
                    # 递归处理下一个学生
                    sub_schemes = simulate_recursive(
                        student_index + 1, new_major_counter, 
                        unsatisfied.copy(), slide.copy(), transfer_assignments.copy()
                    )
                    all_schemes.extend(sub_schemes)
                    assigned = True
                    break
            
            if not assigned:
                # 承诺专业无法满足，有承诺专业的学生不能调剂，直接加入未满足列表
                new_unsatisfied = unsatisfied.copy()
                new_unsatisfied.append(student)
                
                sub_schemes = simulate_recursive(
                    student_index + 1, major_counter,
                    new_unsatisfied, slide.copy(), transfer_assignments.copy()
                )
                all_schemes.extend(sub_schemes)
        else:
            # 没有承诺专业，按意向专业分配
            intended_list = student.get_intended_majors_list()
            assigned = False
            
            for major in intended_list:
                if major in available_majors and available_majors[major] > len(major_counter[major]):
                    new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                    new_major_counter[major].append(student)
                    
                    # 递归处理下一个学生
                    sub_schemes = simulate_recursive(
                        student_index + 1, new_major_counter,
                        unsatisfied.copy(), slide.copy(), transfer_assignments.copy()
                    )
                    all_schemes.extend(sub_schemes)
                    assigned = True
                    break
            
            if not assigned:
                # 意向专业无法满足
                if student.accepts_transfer:
                    # 服从调剂，尝试分配到其他有名额的专业
                    available_for_transfer = []
                    for major, quota in available_majors.items():
                        if quota > len(major_counter[major]):
                            available_for_transfer.append(major)
                    
                    if available_for_transfer:
                        # 为每个可分配的专业创建一个分支
                        for major in available_for_transfer:
                            new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                            new_major_counter[major].append(student)
                            
                            new_transfer_assignments = transfer_assignments.copy()
                            new_transfer_assignments.append({
                                'student': student,
                                'assigned_major': major,
                                'intended_majors': intended_list
                            })
                            
                            # 递归处理下一个学生
                            sub_schemes = simulate_recursive(
                                student_index + 1, new_major_counter,
                                unsatisfied.copy(), slide.copy(), new_transfer_assignments
                            )
                            all_schemes.extend(sub_schemes)
                    else:
                        # 没有可调剂的专业，加入滑档列表
                        new_slide = slide.copy()
                        new_slide.append(student)
                        
                        sub_schemes = simulate_recursive(
                            student_index + 1, major_counter,
                            unsatisfied.copy(), new_slide, transfer_assignments.copy()
                        )
                        all_schemes.extend(sub_schemes)
                else:
                    # 不服从调剂，加入滑档列表
                    new_slide = slide.copy()
                    new_slide.append(student)
                    
                    sub_schemes = simulate_recursive(
                        student_index + 1, major_counter,
                        unsatisfied.copy(), new_slide, transfer_assignments.copy()
                    )
                    all_schemes.extend(sub_schemes)
        
        return all_schemes
    
    # 初始化专业计数器
    initial_major_counter = {major: [] for major in available_majors.keys()}
    
    # 开始递归模拟
    all_schemes = simulate_recursive(0, initial_major_counter, [], [], [])
    
    return all_schemes


def simulate_major_assignment(s_list: List[Student], available_majors: dict) -> tuple:
    """
    模拟专业分配算法
    
    Args:
        s_list: 学生列表
        available_majors: 可用专业字典，格式为 {'专业名称': 录取名额}
    
    Returns:
        tuple: (major_counter, unsatisfied, slide)
        - major_counter: 各专业录取的学生列表，格式为 {'专业名称': [学生列表]}
        - unsatisfied: 不能满足承诺专业从而没有去向的学生列表
        - slide: 没有保专业但录取滑档的学生列表
    """
    
    # 初始化专业计数器
    major_counter = {major: [] for major in available_majors.keys()}
    
    # 维护不能满足承诺专业从而没有去向的学生列表
    unsatisfied = []
    # 维护没有保专业但录取滑档的学生列表
    slide = []
    
    # 使用冒泡排序：按位次优先，同位次时比较数学+语文分数
    sorted_students = bubble_sort_students(s_list)
    
    # 计算总计划数
    total_quota = sum(available_majors.values())
    
    # 只取前总计划数个学生进行模拟
    if len(sorted_students) > total_quota:
        sorted_students = sorted_students[:total_quota]
        print(f"学生总数({len(s_list)})超过计划总数({total_quota})，只考虑前{total_quota}个学生进行模拟")
    
    # 模拟报考逻辑
    for student in sorted_students:
        promised_list = student.get_promised_major_list()
        
        if promised_list:
            # 有承诺专业的学生，优先按承诺专业分配
            flag = False
            for major in promised_list:
                if major in available_majors and available_majors[major] > len(major_counter[major]):
                    major_counter[major].append(student)
                    flag = True
                    break
            if not flag:
                unsatisfied.append(student)
        else:
            # 没有承诺专业，按意向专业分配
            intended_list = student.get_intended_majors_list()
            flag = False
            for major in intended_list:
                if major in available_majors and available_majors[major] > len(major_counter[major]):
                    major_counter[major].append(student)
                    flag = True
                    break
            if not flag:
                slide.append(student)
    
    return major_counter, unsatisfied, slide


def xlsx_to_json(xlsx_file_path: str, json_file_path: str) -> None:
    """
    将Excel文件转换为JSON格式
    
    Args:
        xlsx_file_path: Excel文件路径
        json_file_path: 输出的JSON文件路径
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(xlsx_file_path)
        
        # 转换为学生数据列表
        students_data = []
        for _, row in df.iterrows():
            # 只提取我们需要的核心字段，处理缺失值
            student_data = {
                "姓名": str(row.get("姓名", "")) if pd.notna(row.get("姓名")) else "",
                "排名": str(row.get("排名", "")) if pd.notna(row.get("排名")) else "",
                "意向专业": str(row.get("意向专业", "")) if pd.notna(row.get("意向专业")) else "",
                "承诺专业": str(row.get("承诺专业", "")) if pd.notna(row.get("承诺专业")) else "",
                "专业类别": str(row.get("专业类别", "")) if pd.notna(row.get("专业类别")) else "",
                "总分": str(row.get("总分", "")) if pd.notna(row.get("总分")) else "",
                "数学分数": str(row.get("数学分数", "")) if pd.notna(row.get("数学分数")) else "",
                "语文分数": str(row.get("语文分数", "")) if pd.notna(row.get("语文分数")) else ""
            }
            students_data.append(student_data)
        
        # 写入JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(students_data, f, ensure_ascii=False, indent=2)
        
        print(f"成功将 {len(students_data)} 名学生数据从 {xlsx_file_path} 转换为 {json_file_path}")
        
    except FileNotFoundError:
        print(f"文件 {xlsx_file_path} 不存在")
    except Exception as e:
        print(f"转换过程中发生错误：{e}")


def simulate_adjustment_based_on_base_scheme(base_scheme: dict, adjusted_plan: dict, students: List[Student]) -> List[dict]:
    """
    基于已有的基础方案和调整后的名额分配，生成新的录取方案
    关键：保持原方案中已调剂学生的去向不变，只重新分配未录取的学生
    
    Args:
        base_scheme: 基础方案，包含 major_counter, unsatisfied, slide, transfer_assignments
        adjusted_plan: 调整后的名额分配方案
        students: 原始学生列表
    
    Returns:
        基于调整方案的新录取结果列表
    """
    
    # 从基础方案中提取信息
    original_major_counter = base_scheme['major_counter']
    original_unsatisfied = base_scheme['unsatisfied']
    original_slide = base_scheme['slide']
    original_transfer_assignments = base_scheme.get('transfer_assignments', [])
    
    # 创建已录取学生的固定分配（包括调剂学生）
    fixed_assignments = {}
    for major, students_in_major in original_major_counter.items():
        fixed_assignments[major] = students_in_major.copy()
    
    # 计算调整后每个专业还有多少名额
    remaining_quota = {}
    for major, adjusted_quota in adjusted_plan.items():
        currently_assigned = len(fixed_assignments.get(major, []))
        remaining_quota[major] = max(0, adjusted_quota - currently_assigned)
    
    # 需要重新分配的学生 = 原来未满足 + 原来滑档的学生
    students_to_reassign = original_unsatisfied + original_slide
    
    if not students_to_reassign:
        # 没有需要重新分配的学生，直接返回调整后的结果
        return [{
            'major_counter': fixed_assignments,
            'unsatisfied': [],
            'slide': [],
            'transfer_assignments': original_transfer_assignments.copy()
        }]
    
    # 对需要重新分配的学生进行模拟（保持原有排序）
    def reassign_recursive(student_index: int, major_counter: dict, unsatisfied: list, 
                          slide: list, transfer_assignments: list, remaining_quotas: dict) -> List[dict]:
        if student_index >= len(students_to_reassign):
            return [{
                'major_counter': {k: v.copy() for k, v in major_counter.items()},
                'unsatisfied': unsatisfied.copy(),
                'slide': slide.copy(),
                'transfer_assignments': transfer_assignments.copy()
            }]
        
        student = students_to_reassign[student_index]
        all_schemes = []
        
        # 检查学生是否有承诺专业
        promised_list = student.get_promised_major_list()
        
        if promised_list:
            # 有承诺专业的学生
            assigned = False
            for major in promised_list:
                if major in remaining_quotas and remaining_quotas[major] > 0:
                    # 可以分配到承诺专业
                    new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                    new_major_counter[major].append(student)
                    
                    new_remaining_quotas = remaining_quotas.copy()
                    new_remaining_quotas[major] -= 1
                    
                    sub_schemes = reassign_recursive(
                        student_index + 1, new_major_counter, unsatisfied.copy(), 
                        slide.copy(), transfer_assignments.copy(), new_remaining_quotas
                    )
                    all_schemes.extend(sub_schemes)
                    assigned = True
                    break
            
            if not assigned:
                # 承诺专业无法满足，有承诺专业的学生不能调剂，直接保持未满足状态
                new_unsatisfied = unsatisfied.copy()
                new_unsatisfied.append(student)
                
                sub_schemes = reassign_recursive(
                    student_index + 1, major_counter, new_unsatisfied,
                    slide.copy(), transfer_assignments.copy(), remaining_quotas
                )
                all_schemes.extend(sub_schemes)
        else:
            # 没有承诺专业，按意向专业分配
            intended_list = student.get_intended_majors_list()
            assigned = False
            
            for major in intended_list:
                if major in remaining_quotas and remaining_quotas[major] > 0:
                    new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                    new_major_counter[major].append(student)
                    
                    new_remaining_quotas = remaining_quotas.copy()
                    new_remaining_quotas[major] -= 1
                    
                    sub_schemes = reassign_recursive(
                        student_index + 1, new_major_counter, unsatisfied.copy(),
                        slide.copy(), transfer_assignments.copy(), new_remaining_quotas
                    )
                    all_schemes.extend(sub_schemes)
                    assigned = True
                    break
            
            if not assigned:
                # 意向专业无法满足
                if student.accepts_transfer:
                    # 服从调剂
                    available_majors = [major for major, quota in remaining_quotas.items() if quota > 0]
                    
                    if available_majors:
                        for major in available_majors:
                            new_major_counter = {k: v.copy() for k, v in major_counter.items()}
                            new_major_counter[major].append(student)
                            
                            new_remaining_quotas = remaining_quotas.copy()
                            new_remaining_quotas[major] -= 1
                            
                            new_transfer_assignments = transfer_assignments.copy()
                            new_transfer_assignments.append({
                                'student': student,
                                'assigned_major': major,
                                'intended_majors': intended_list
                            })
                            
                            sub_schemes = reassign_recursive(
                                student_index + 1, new_major_counter, unsatisfied.copy(),
                                slide.copy(), new_transfer_assignments, new_remaining_quotas
                            )
                            all_schemes.extend(sub_schemes)
                    else:
                        # 没有可调剂的专业，滑档
                        new_slide = slide.copy()
                        new_slide.append(student)
                        
                        sub_schemes = reassign_recursive(
                            student_index + 1, major_counter, unsatisfied.copy(),
                            new_slide, transfer_assignments.copy(), remaining_quotas
                        )
                        all_schemes.extend(sub_schemes)
                else:
                    # 不服从调剂，滑档
                    new_slide = slide.copy()
                    new_slide.append(student)
                    
                    sub_schemes = reassign_recursive(
                        student_index + 1, major_counter, unsatisfied.copy(),
                        new_slide, transfer_assignments.copy(), remaining_quotas
                    )
                    all_schemes.extend(sub_schemes)
        
        return all_schemes
    
    # 开始重新分配
    adjusted_schemes = reassign_recursive(0, fixed_assignments, [], [], original_transfer_assignments.copy(), remaining_quota)
    
    return adjusted_schemes


if __name__ == "__main__":
    
    # 基础专业分配模拟
    print("=== 专业分配模拟数据 ===")
    db = StudentDatabase()
    
    # 从Excel文件加载学生信息
    db.load_from_xlsx("工作簿2.xlsx")
    
    # 招生计划
    admission_plan = {
        '汉语言文学': 1,
        '德语(德语法学实验班)': 1,
        '经济管理试验班(数智经济与管理)': 4,
        '社会科学试验班': 5,
        '人文科学试验班': 2,
        '英语': 1
    }
    
    print(f"\n招生计划：")
    for major, capacity in admission_plan.items():
        print(f"  {major}: {capacity}个名额")
    
    print(f"\n学生总数: {len(db.students)}名")
    
    # 执行专业分配模拟
    major_counter, unsatisfied, slide = simulate_major_assignment(db.students, admission_plan)
    
    # 显示录取结果
    print(f"\n" + "="*50)
    print("录取结果")
    print("="*50)
    
    total_admitted = 0
    for major, students in major_counter.items():
        admitted_count = len(students)
        total_admitted += admitted_count
        quota = admission_plan[major]
        
        print(f"\n【{major}】- {admitted_count}/{quota}")
        
        if students:
            for i, student in enumerate(students):
                print(f"  {i+1}. {student.name} (排名{student.rank}, 总分{student.total_score})")
        
        if admitted_count < quota:
            print(f"  空余名额: {quota - admitted_count}个")
    
    print(f"\n总录取人数: {total_admitted}")
    
    # 显示未满足承诺专业的学生
    print(f"\n" + "="*50)
    print(f"未满足承诺专业学生 ({len(unsatisfied)}人)")
    print("="*50)
    
    if unsatisfied:
        for i, student in enumerate(unsatisfied):
            promised_majors = student.get_promised_major_list()
            print(f"{i+1}. {student.name} (排名{student.rank}, 总分{student.total_score})")
            print(f"   承诺专业: {', '.join(promised_majors)}")
    else:
        print("无")
    
    # 显示滑档学生
    print(f"\n" + "="*50)
    print(f"滑档学生 ({len(slide)}人)")
    print("="*50)
    
    if slide:
        for i, student in enumerate(slide):
            intended_majors = student.get_intended_majors_list()
            print(f"{i+1}. {student.name} (排名{student.rank}, 总分{student.total_score})")
            print(f"   意向专业: {', '.join(intended_majors[:3])}{'...' if len(intended_majors) > 3 else ''}")
    else:
        print("无")
    
    # 名额调整功能 - 基于首次模拟结果动态确定可减专业
    print(f"\n" + "="*50)
    print("名额调整方案")
    print("="*50)
    
    # 识别空余名额的专业（可减专业）- 基于首次模拟结果
    reducible_majors_dict = {}
    for major, quota in admission_plan.items():
        admitted_count = len(major_counter[major])
        if admitted_count < quota:
            reducible_majors_dict[major] = quota - admitted_count  # 空余名额数
    
    if not reducible_majors_dict:
        print("所有专业都已招满，无法调整名额")
    else:
        print(f"可减专业及空余名额: {reducible_majors_dict}")
        
        # 获取可增加名额的专业（非减专业，即已招满的专业）
        increasable_majors = [major for major in admission_plan.keys() if major not in reducible_majors_dict.keys()]
        print(f"可增加名额的专业: {increasable_majors}")
        
        # 生成所有调整方案
        adjustment_schemes = generate_adjustment_schemes(
            admission_plan, major_counter, reducible_majors_dict, increasable_majors
        )
        
        print(f"\n生成了 {len(adjustment_schemes)} 种调整方案:")
        
        # 对每种调整方案进行模拟
        for i, adjusted_plan in enumerate(adjustment_schemes):
            print(f"\n--- 调整方案 {i+1} ---")
            print("调整后名额分配:")
            for major, quota in adjusted_plan.items():
                original = admission_plan[major]
                change = quota - original
                change_str = f" ({change:+d})" if change != 0 else ""
                print(f"  {major}: {quota}{change_str}")
            
            # 用调整后的计划重新模拟
            adj_major_counter, adj_unsatisfied, adj_slide = simulate_major_assignment(db.students, adjusted_plan)
            
            adj_total_admitted = sum(len(students) for students in adj_major_counter.values())
            print(f"调整后录取人数: {adj_total_admitted}")
            print(f"调整后未满足承诺: {len(adj_unsatisfied)}人")
            print(f"调整后滑档: {len(adj_slide)}人") 