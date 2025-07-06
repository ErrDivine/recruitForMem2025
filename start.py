#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京大学招生助手系统启动脚本
"""

import os
import sys
import subprocess
import webbrowser
from time import sleep

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 错误：需要Python 3.8或更高版本")
        print(f"   当前版本：Python {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python版本检查通过：{version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖是否安装"""
    required_packages = [
        'flask',
        'pandas', 
        'openpyxl',
        'werkzeug'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少以下依赖：{', '.join(missing_packages)}")
        print("📦 请运行：pip install -r requirements.txt")
        return False
    
    print("✅ 主要依赖检查通过")
    return True

def create_upload_dir():
    """创建上传目录"""
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        print(f"📁 创建上传目录：{upload_dir}")
    else:
        print(f"✅ 上传目录已存在：{upload_dir}")
    return True

def install_dependencies():
    """安装依赖"""
    print("🔧 正在安装依赖...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        return False

def start_application():
    """启动应用"""
    print("🚀 启动南京大学招生助手系统...")
    
    # 设置环境变量
    os.environ['FLASK_APP'] = 'front_end/app.py'
    os.environ['FLASK_ENV'] = 'development'
    
    app_path = os.path.join(os.path.dirname(__file__), 'front_end', 'app.py')
    
    try:
        # 延迟打开浏览器
        def open_browser():
            sleep(2)
            webbrowser.open('http://localhost:5021')
        
        # 在后台线程中打开浏览器
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # 启动Flask应用
        subprocess.run([sys.executable, app_path], check=True)
        
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败：{str(e)}")

def main():
    """主函数"""
    print("=" * 50)
    print("🎓 南京大学招生助手系统")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        return
    
    # 检查依赖
    if not check_dependencies():
        install_deps = input("是否自动安装依赖？(y/n): ").lower().strip()
        if install_deps in ['y', 'yes']:
            if not install_dependencies():
                input("按回车键退出...")
                return
        else:
            input("按回车键退出...")
            return
    
    # 创建必要目录
    create_upload_dir()
    
    print("\n🌟 系统功能：")
    print("   • 名额分配分析 - 智能生成最优录取方案")
    print("   • 文件上传管理 - 支持Excel格式考生数据")
    print("   • 数据统计分析 - 全面的招生数据洞察")
    
    print("\n📋 使用说明：")
    print("   1. 准备好Excel格式的考生信息文件")
    print("   2. 访问 http://localhost:5021 使用系统")
    print("   3. 上传文件并进行名额分配分析")
    print("   4. 按 Ctrl+C 停止系统")
    
    print("\n" + "=" * 50)
    
    # 启动应用
    start_application()

if __name__ == "__main__":
    main() 