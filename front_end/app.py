import os
import sys
from typing import Any, Dict, List
import tempfile
import shutil

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# 将后端目录加入 Python 路径
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "back_end"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 将项目根目录加入 Python 路径以导入 student_simulation
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import student_simulation as sim  # noqa: E402  导入模拟分析模块

app = Flask(__name__)
app.config.update(
    SECRET_KEY="njurecruit",
    MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 限制上传文件大小为50MB
    UPLOAD_FOLDER=os.path.join(PROJECT_ROOT, 'uploads')
)

# 确保上传文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """首页：展示招生系统功能入口"""
    return render_template("index.html")

@app.route("/allocation_analysis")
def allocation_analysis():
    """名额分配分析页面"""
    return render_template("allocation_analysis.html")

@app.route("/student_management")
def student_management():
    """考生信息管理页面"""
    return render_template("student_management.html")

@app.route("/phone_mode")
def phone_mode():
    """Phone Mode - 快速电话联系模式"""
    return render_template("phone_mode.html")

@app.route("/search_mode")
def search_mode():
    """Search Mode - 高级搜索查询模式"""
    return render_template("search_mode.html")

def _json_response(data: Any, status: int = 200):
    """统一 JSON 包装格式。"""
    return jsonify({"code": 0, "data": data}), status

@app.route("/api/run_analysis", methods=["POST"])
def api_run_analysis():
    try:
        # 获取表单数据
        subject_type = request.form.get('subject_type')
        uploaded_file = request.files.get('excel_file')
        
        if not uploaded_file or not allowed_file(uploaded_file.filename):
            return jsonify({"code": 1, "msg": "请选择有效的Excel文件"}), 400
        
        # 获取招生计划
        admission_plan = {}
        major_index = 0
        while True:
            major_key = f'major_{major_index}'
            if major_key not in request.form:
                break
            quota = request.form.get(major_key)
            major_name = request.form.get(f'major_name_{major_index}')
            if major_name and quota:
                admission_plan[major_name] = int(quota)
            major_index += 1
        
        if not admission_plan:
            return jsonify({"code": 1, "msg": "请配置招生计划"}), 400
        
        # 创建临时文件
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uploaded_file.filename}")
        uploaded_file.save(temp_file_path)
        
        try:
            # 加载学生数据
            db = sim.StudentDatabase()
            db.load_from_xlsx(temp_file_path)
            
            if not db.students:
                return jsonify({"code": 1, "msg": "无法加载学生数据"}), 400
        
            # 确定可减少名额的专业（根据文理科配置）
            if subject_type == "liberal_arts":
                reducible_majors = ["德语(德语法学实验班)", "英语"]
                max_reduction = {
                    "德语(德语法学实验班)": 1,
                    "英语": 1
                }
            else:  # science
                # 修正理科可减少专业配置，匹配实际的专业名称
                reducible_majors = ["理科试验班类（数理科学类）", "理科试验班类（化学与生命科学类）"] 
                max_reduction = {
                    "理科试验班类（数理科学类）": 1,
                    "理科试验班类（化学与生命科学类）": 1
                }
            
            # 过滤出实际存在于招生计划中的可减少专业
            actual_reducible_majors = [major for major in reducible_majors if major in admission_plan]
            actual_max_reduction = {major: max_reduction.get(major, 1) for major in actual_reducible_majors}
            
            print(f"可减少专业: {actual_reducible_majors}")
            print(f"最大减少量: {actual_max_reduction}")
            
            # === 第一层：生成带调剂的原始基础方案 ===
            print("开始生成带调剂的原始基础方案...")
            base_schemes = sim.simulate_major_assignment_with_transfer(db.students, admission_plan)
            print(f"生成了 {len(base_schemes)} 个原始基础方案")
            
            if not base_schemes:
                return jsonify({"code": 1, "msg": "无法生成基础方案"}), 400
            
            # 转换基础方案格式
            def format_base_scheme_for_frontend(scheme, scheme_id, original_plan):
                """将基础方案转换为前端格式"""
                major_counter = scheme['major_counter']
                unsatisfied = scheme['unsatisfied']
                slide = scheme['slide']
                transfer_assignments = scheme.get('transfer_assignments', [])
                
                # 转换专业录取结果
                major_results = {}
                for major, quota in original_plan.items():
                    admitted_students = major_counter.get(major, [])
                    admitted_count = len(admitted_students)
                    vacancy = quota - admitted_count
                    
                    major_results[major] = {
                        'admitted_count': admitted_count,
                        'quota': quota,
                        'vacancy': vacancy,
                        'students': [
                            {
                                'name': s.name,
                                'rank': s.rank,
                                'score': s.total_score
                            } for s in admitted_students
                        ]
                    }
                
                # 转换未满足学生
                unsatisfied_students = [
                    {
                        'name': s.name,
                        'rank': s.rank,
                        'score': s.total_score,
                        'intended_majors': s.intended_majors.split('/') if hasattr(s, 'intended_majors') and s.intended_majors else []
                    } for s in unsatisfied
                ]
                
                # 转换滑档学生  
                slide_students = [
                    {
                        'name': s.name,
                        'rank': s.rank,
                        'score': s.total_score,
                        'intended_majors': s.intended_majors.split('/') if hasattr(s, 'intended_majors') and s.intended_majors else []
                    } for s in slide
                ]
                
                # 转换调剂学生
                transfer_students = [
                    {
                        'name': assignment['student'].name,
                        'rank': assignment['student'].rank,
                        'score': assignment['student'].total_score,
                        'intended_majors': assignment['intended_majors'],
                        'assigned_major': assignment['assigned_major']
                    } for assignment in transfer_assignments
                ]
                
                # 检查是否有空余名额
                has_vacancy = any(vacancy > 0 for vacancy in [major_results[major]['vacancy'] for major in major_results])
                total_vacancy = sum(major_results[major]['vacancy'] for major in major_results)
                vacant_majors = [f"{major}({major_results[major]['vacancy']})" 
                               for major in major_results if major_results[major]['vacancy'] > 0]
                
                return {
                    'scheme_id': scheme_id,
                    'allocation': original_plan,
                    'major_results': major_results,
                    'unsatisfied_count': len(unsatisfied),
                    'unsatisfied_students': unsatisfied_students,
                    'slide_count': len(slide), 
                    'slide_students': slide_students,
                    'transfer_count': len(transfer_assignments),
                    'transfer_students': transfer_students,
                    'total_admitted': sum(len(students) for students in major_counter.values()),
                    'total_quota': sum(original_plan.values()),
                    'has_vacancy': has_vacancy,
                    'total_vacancy': total_vacancy,
                    'vacant_majors': vacant_majors
                }
            
            # 按优先级排序基础方案（未满足+滑档越少越好）
            sorted_base_schemes = sorted(base_schemes, 
                                       key=lambda x: (len(x['unsatisfied']) + len(x['slide']), 
                                                    len(x['slide']),
                                                    len(x['unsatisfied'])))
            
            # 转换为前端格式
            original_base_schemes = []
            for i, scheme in enumerate(sorted_base_schemes):
                formatted_scheme = format_base_scheme_for_frontend(scheme, i + 1, admission_plan)
                original_base_schemes.append(formatted_scheme)
                print(f"方案{i+1}: 有空余={formatted_scheme['has_vacancy']}, 空余数={formatted_scheme['total_vacancy']}, 空余专业={formatted_scheme['vacant_majors']}")
            
            # 计算完美方案（未满足=0且滑档=0）
            perfect_schemes = [scheme for scheme in original_base_schemes 
                             if scheme['unsatisfied_count'] == 0 and scheme['slide_count'] == 0]
            
            # === 第二层：为有空余名额的基础方案生成调整方案 ===
            base_schemes_with_adjustments = []
            total_adjustment_plans = 0
            
            print("\n开始生成基于基础方案的名额调整方案...")
            for base_scheme_data in original_base_schemes[:10]:  # 只为前10个基础方案生成调整方案
                if base_scheme_data['has_vacancy'] and base_scheme_data['total_vacancy'] > 0:
                    # 生成该基础方案的调整方案
                    adjustment_plans = generate_adjustment_plans_from_base_scheme(
                        base_scheme_data, admission_plan, actual_reducible_majors, sorted_base_schemes, db.students
                    )
                    
                    if adjustment_plans:
                        base_schemes_with_adjustments.append({
                            'base_scheme_index': base_scheme_data['scheme_id'],
                            'adjustment_plans': adjustment_plans
                        })
                        total_adjustment_plans += len(adjustment_plans)
            
            print(f"生成了 {total_adjustment_plans} 个调整方案")
            
            # 计算方案统计
            schemes_with_vacancy = [s for s in original_base_schemes if s['has_vacancy']]
            schemes_without_vacancy = [s for s in original_base_schemes if not s['has_vacancy']]
            
            # 构建返回数据
            result_data = {
                'subject_type': subject_type,  # 添加科类信息
                'total_students': len(db.students),
                'original_total_students': len(db.students),  # 原始学生总数
                'actual_student_count': min(len(db.students), sum(admission_plan.values())),
                'total_quota': sum(admission_plan.values()),
                'original_plan': admission_plan,
                'original_base_schemes': original_base_schemes,
                'base_schemes_with_adjustments': base_schemes_with_adjustments,
                'total_adjustment_plans': total_adjustment_plans,
                'perfect_schemes': perfect_schemes,
                'has_perfect_scheme': len(perfect_schemes) > 0,
                'schemes_with_vacancy_count': len(schemes_with_vacancy),  # 有空余的方案数
                'schemes_without_vacancy_count': len(schemes_without_vacancy),  # 无空余的方案数
                'analysis_summary': {
                    'total_base_schemes': len(original_base_schemes),
                    'schemes_with_vacancy': len(schemes_with_vacancy),
                    'perfect_schemes_count': len(perfect_schemes)
                },
                'total_schemes_analyzed': len(base_schemes)
            }
            
            return _json_response(result_data)
            
        except Exception as e:
            return jsonify({"code": 1, "msg": f"分析失败: {str(e)}"}), 500
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        return jsonify({"code": 1, "msg": f"分析失败: {str(e)}"}), 500


def generate_adjustment_plans_from_base_scheme(base_scheme_data, original_plan, reducible_majors, sorted_base_schemes, students):
    """基于基础方案生成调整方案"""
    adjustment_plans = []
    
    # 找到对应的原始基础方案对象
    base_scheme_index = base_scheme_data['scheme_id'] - 1  # 转换为0基础索引
    if base_scheme_index >= len(sorted_base_schemes):
        return adjustment_plans
    
    original_base_scheme = sorted_base_schemes[base_scheme_index]
    
    # 转换调整后的方案为前端格式的函数
    def format_adjusted_scheme_for_frontend(adjusted_scheme, plan):
        major_counter = adjusted_scheme['major_counter']
        unsatisfied = adjusted_scheme['unsatisfied']
        slide = adjusted_scheme['slide']
        transfer_assignments = adjusted_scheme.get('transfer_assignments', [])
        
        major_results = {}
        for major, quota in plan.items():
            admitted = major_counter.get(major, [])
            major_results[major] = {
                'admitted_count': len(admitted),
                'quota': quota,
                'vacancy': quota - len(admitted),
                'students': [{'name': s.name, 'rank': s.rank, 'score': s.total_score} for s in admitted]
            }
        
        return {
            'scheme_id': 1,
            'major_results': major_results,
            'unsatisfied_count': len(unsatisfied),
            'slide_count': len(slide),
            'transfer_count': len(transfer_assignments),
            'total_admitted': sum(len(students) for students in major_counter.values()),
            'unsatisfied_students': [{'name': s.name, 'rank': s.rank, 'score': s.total_score} for s in unsatisfied],
            'slide_students': [{'name': s.name, 'rank': s.rank, 'score': s.total_score} for s in slide],
            'transfer_students': [
                {
                    'name': assignment['student'].name,
                    'rank': assignment['student'].rank,
                    'score': assignment['student'].total_score,
                    'intended_majors': assignment['intended_majors'],
                    'assigned_major': assignment['assigned_major']
                } for assignment in transfer_assignments
            ]
        }
    
    # 检查哪些专业有空余名额
    vacant_majors = {}
    for major in base_scheme_data['major_results']:
        vacancy = base_scheme_data['major_results'][major]['vacancy']
        if vacancy > 0:
            vacant_majors[major] = vacancy
    
    if not vacant_majors:
        return adjustment_plans
    
    # 筛选可以减少名额的专业（需要既有空余又在可减少列表中）
    reducible_vacant_majors = {major: vacancy for major, vacancy in vacant_majors.items() 
                              if major in reducible_majors}
    
    print(f"所有空余专业: {vacant_majors}")
    print(f"可减少的空余专业: {reducible_vacant_majors}")
    
    # 如果没有可减少的空余专业，但有其他空余专业，我们可以采用不同的调整策略
    if not reducible_vacant_majors:
        # 策略：从有空余的专业中减少名额，分配给其他专业
        for major_to_reduce, vacancy in vacant_majors.items():
            max_reduction = min(vacancy, 2)  # 最多减2个名额
            
            for reduction in range(1, max_reduction + 1):
                # 创建调整后的计划
                adjusted_plan = original_plan.copy()
                adjusted_plan[major_to_reduce] -= reduction
                
                # 将减少的名额分配给名额不足的专业
                deficit_majors = [m for m in original_plan.keys() 
                                 if m != major_to_reduce and 
                                 base_scheme_data['major_results'][m]['vacancy'] == 0]
                
                if deficit_majors:
                    # 简单策略：平均分配给名额不足的专业
                    quota_per_major = reduction // len(deficit_majors)
                    remaining = reduction % len(deficit_majors)
                    
                    for i, major in enumerate(deficit_majors):
                        adjusted_plan[major] += quota_per_major
                        if i < remaining:
                            adjusted_plan[major] += 1
                    
                    # 计算变化
                    plan_changes = {}
                    for major in original_plan:
                        change = adjusted_plan[major] - original_plan[major]
                        if change != 0:
                            plan_changes[major] = change
                    
                    # 生成调整方案
                    try:
                        adjusted_schemes = sim.simulate_adjustment_based_on_base_scheme(
                            original_base_scheme, adjusted_plan, students
                        )
                        
                        base_schemes = []
                        for adjusted_scheme in adjusted_schemes:
                            formatted_scheme = format_adjusted_scheme_for_frontend(adjusted_scheme, adjusted_plan)
                            base_schemes.append(formatted_scheme)
                        
                        adjustment_plans.append({
                            'plan_name': f"减少{major_to_reduce}{reduction}个名额",
                            'plan_changes': plan_changes,
                            'adjusted_plan': adjusted_plan,
                            'base_schemes': base_schemes,
                            'scheme_count': len(base_schemes)
                        })
                        
                    except Exception as e:
                        print(f"调整方案模拟失败: {e}")
                        continue
        
        return adjustment_plans
    
    # 生成调整方案（基于可减少的空余名额进行调整）
    for major_to_reduce in reducible_vacant_majors:
        max_reduction = min(reducible_vacant_majors[major_to_reduce], 2)  # 最多减2个名额
        
        for reduction in range(1, max_reduction + 1):
            # 创建调整后的计划
            adjusted_plan = original_plan.copy()
            adjusted_plan[major_to_reduce] -= reduction
            
            # 将减少的名额分配给其他专业
            other_majors = [m for m in original_plan.keys() if m != major_to_reduce]
            if other_majors:
                # 简单策略：平均分配给其他专业
                quota_per_major = reduction // len(other_majors)
                remaining = reduction % len(other_majors)
                
                for i, major in enumerate(other_majors):
                    adjusted_plan[major] += quota_per_major
                    if i < remaining:
                        adjusted_plan[major] += 1
                
                # 计算变化
                plan_changes = {}
                for major in original_plan:
                    change = adjusted_plan[major] - original_plan[major]
                    if change != 0:
                        plan_changes[major] = change
                
                # === 第三层：使用调整后的方案重新生成录取方案（保持调剂方向不变）===
                try:
                    # 使用 simulate_adjustment_based_on_base_scheme 保持调剂方向
                    adjusted_schemes = sim.simulate_adjustment_based_on_base_scheme(
                        original_base_scheme, adjusted_plan, students
                    )
                    
                    base_schemes = []
                    for adjusted_scheme in adjusted_schemes:
                        formatted_scheme = format_adjusted_scheme_for_frontend(adjusted_scheme, adjusted_plan)
                        base_schemes.append(formatted_scheme)
                    
                    adjustment_plans.append({
                        'plan_name': f"减少{major_to_reduce}{reduction}个名额",
                        'plan_changes': plan_changes,
                        'adjusted_plan': adjusted_plan,
                        'base_schemes': base_schemes,
                        'scheme_count': len(base_schemes)
                    })
                    
                except Exception as e:
                    print(f"调整方案模拟失败: {e}")
                    continue
    
    return adjustment_plans

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5022, debug=True) 