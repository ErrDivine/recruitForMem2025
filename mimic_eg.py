from student_simulation import Student



#假设有ABCDE五名考生
A,B,C,D,E = Student()
s_list = list(A,B,C,D,E)


#假设专业如下,为 专业名称---录取名额 的键值对
available_majors = {'math':1, 'physics':2, 'chemistry':1}

#用于记录每个专业已经录入的学生
major_counter = {'math':[], 'physics':[], 'chemistry':[]}


#排序算法，给ABCDE按省排名由低到高排序（省排名越小，录取优先级越高）
o_list = sorted(s_list, key=lambda student: student.rank_int)

# 或者使用冒泡排序算法实现
def bubble_sort_by_rank(student_list):
    """冒泡排序：按省排名从低到高排序（省排名越小，录取优先级越高）"""
    n = len(student_list)
    # 创建副本避免修改原列表
    sorted_list = student_list.copy()
    
    for i in range(n):
        for j in range(0, n - i - 1):
            # 如果当前学生省排名大于下一个学生省排名，则交换
            if sorted_list[j].rank_int > sorted_list[j + 1].rank_int:
                sorted_list[j], sorted_list[j + 1] = sorted_list[j + 1], sorted_list[j]
    
    return sorted_list



#维护不能满足承诺专业从而没有去向的学生列表
unsatisfied = []
#维护没有保专业但录取滑档的学生列表
slide = []


#模拟报考逻辑
for student in o_list:
    promised_list = student.get_promised_major_list()
    if promised_list:
        flag = False
        for major in promised_list:
            if available_majors[major] > len(major_counter[major]):
                major_counter[major].append(student)
                flag = True
                break
        if not flag:
            unsatisfied.append(student)

    else:
        intended_list = student.get_intended_majors_list()
        flag = False
        for major in intended_list:
            if available_majors[major] > len(major_counter[major]):
                major_counter[major].append(student)
                flag = True
                break
        if not flag:
            slide.append(student)






