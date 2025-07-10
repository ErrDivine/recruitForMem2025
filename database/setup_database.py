#!/usr/bin/env python3
"""
数据库初始化脚本
用于快速搭建南京大学招生助手系统的数据库环境
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import init_database, db_manager, DatabaseConfig

def setup_database():
    """设置数据库"""
    print("=" * 60)
    print("🎓 南京大学招生助手系统 - 数据库初始化")
    print("=" * 60)
    
    # 获取当前脚本目录
    current_dir = Path(__file__).parent
    sql_file = current_dir / "create_tables.sql"
    
    print(f"📁 SQL文件路径: {sql_file}")
    
    # 检查SQL文件是否存在
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return False
    
    print("🔗 正在连接数据库...")
    try:
        # 测试数据库连接
        with db_manager.get_connection() as conn:
            print("✅ 数据库连接成功")
        
        print("📊 正在执行建表脚本...")
        success = init_database(str(sql_file))
        
        if success:
            print("✅ 数据库初始化完成！")
            print("\n🎉 数据库设置成功！包含以下表：")
            print("   • majors - 专业信息表")
            print("   • students - 学生信息表") 
            print("   • crew_base - 工作人员基础表")
            print("   • crew_members - 普通工作人员表")
            print("   • crew_leaders - 工作人员负责人表")
            print("   • student_intended_majors - 学生意向专业关联表")
            print("   • student_promise_majors - 学生承诺专业关联表")
            print("   • student_due_chargers - 学生负责人关联表")
            print("   • student_records - 学生沟通记录表")
            print("   • crew_worklist - 工作人员联系学生列表")
            print("   • crew_work_files - 工作文件表（支持网页访问）")
            
            print("\n🔑 默认管理员账户:")
            print("   账号: admin")
            print("   密码: admin123")
            print("   ⚠️  请在生产环境中修改默认密码！")
            
            print("\n📝 示例专业数据已插入，包括:")
            print("   文科: 人文科学试验班、汉语言文学、英语、德语(德语法学实验班)")
            print("   理科: 理科试验班类、计算机科学与技术、软件工程")
            
            return True
        else:
            print("❌ 数据库初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n💡 请检查以下配置:")
        print("   1. MySQL服务是否正在运行")
        print("   2. 数据库连接参数是否正确")
        print("   3. 用户是否有足够的权限")
        print("\n🔧 配置文件位置: database/config.py")
        print("🔧 环境变量示例: database/env_example.txt")
        return False

def show_config_info():
    """显示配置信息"""
    config = db_manager.config
    print(f"\n📋 当前数据库配置:")
    print(f"   主机: {config.host}")
    print(f"   端口: {config.port}")
    print(f"   用户: {config.user}")
    print(f"   数据库: {config.database}")
    print(f"   字符集: {config.charset}")

def main():
    """主函数"""
    try:
        show_config_info()
        
        # 询问用户是否继续
        confirm = input("\n❓ 是否继续初始化数据库？(y/n): ").lower().strip()
        if confirm not in ['y', 'yes']:
            print("👋 取消初始化")
            return
        
        success = setup_database()
        
        if success:
            print("\n🚀 现在您可以:")
            print("   1. 运行 python start.py 启动系统")
            print("   2. 访问 http://localhost:5021 使用系统")
            print("   3. 上传Excel文件进行学生信息管理")
        else:
            print("\n🔧 如需帮助，请检查:")
            print("   1. database/config.py - 数据库配置")
            print("   2. database/env_example.txt - 环境变量示例")
            print("   3. requirements.txt - 确保安装了PyMySQL")
            
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
    except Exception as e:
        print(f"\n❌ 初始化过程中发生错误: {e}")

if __name__ == "__main__":
    main() 