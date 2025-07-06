#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import re

class SingleThreadRecruitSpider:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """设置Chrome浏览器。"""
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except:
            self.driver = webdriver.Chrome(options=options)
            
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self):
        """登录系统。"""
        print("打开登录页...")
        self.driver.get("https://recruit-student.tbs-datum.com/#/login")
        time.sleep(2)
        
        print("提交登录信息...")
        username_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[placeholder*='用户'], input[placeholder*='账号']")))
        username_input.clear()
        username_input.send_keys("HLJ1")
        
        password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[placeholder*='密码']")
        password_input.clear()
        password_input.send_keys("00000000")
        
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button:contains('登录'), .el-button--primary")
        login_button.click()
        
        time.sleep(3)
        print(f"登录成功，当前页面： {self.driver.current_url}")
        
    def test_single_student_info_extraction(self):
        """测试单个学生信息提取。"""
        # 等待页面加载
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(2)
        
        # 获取第一个学生的信息
        rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if len(rows) == 0:
            print("没有找到学生数据")
            return
            
        first_row = rows[0]
        cells = first_row.find_elements(By.TAG_NAME, "td")
        student_name = cells[0].text.strip() if cells else "未知"
        
        print(f"\n=== 测试学生: {student_name} ===")
        
        # 测试编辑信息提取
        edit_info = self.test_edit_info_extraction(first_row, student_name)
        print(f"编辑信息: {json.dumps(edit_info, ensure_ascii=False, indent=2)}")
        
        # 测试沟通记录提取
        comm_info = self.test_communication_info_extraction(first_row, student_name)
        print(f"沟通记录: {json.dumps(comm_info, ensure_ascii=False, indent=2)}")
        
    def test_edit_info_extraction(self, row, student_name):
        """测试编辑信息提取。"""
        try:
            # 查找编辑按钮
            edit_buttons = row.find_elements(By.CSS_SELECTOR, "button")
            edit_button = None
            
            for btn in edit_buttons:
                if "编辑" in btn.text:
                    edit_button = btn
                    break
                    
            if not edit_button:
                print("未找到编辑按钮")
                return {}
                
            print("点击编辑按钮...")
            self.driver.execute_script("arguments[0].click();", edit_button)
            
            # 等待弹窗出现
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".el-dialog")))
            time.sleep(2)
            
            # 获取弹窗HTML
            html = self.driver.page_source
            edit_info = self.parse_edit_dialog(html)
            
            # 关闭弹窗
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".el-dialog__close, .el-dialog .el-button--default")
                if close_buttons:
                    self.driver.execute_script("arguments[0].click();", close_buttons[0])
                time.sleep(1)
            except:
                pass
                
            return edit_info
            
        except Exception as e:
            print(f"提取编辑信息失败: {e}")
            return {}
            
    def test_communication_info_extraction(self, row, student_name):
        """测试沟通记录提取。"""
        try:
            # 查找沟通记录按钮
            comm_buttons = row.find_elements(By.CSS_SELECTOR, "button")
            comm_button = None
            
            for btn in comm_buttons:
                if "沟通记录" in btn.text or "交流记录" in btn.text:
                    comm_button = btn
                    break
                    
            if not comm_button:
                print("未找到沟通记录按钮")
                return {}
                
            print("点击沟通记录按钮...")
            self.driver.execute_script("arguments[0].click();", comm_button)
            
            # 等待弹窗出现
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".el-dialog")))
            time.sleep(2)
            
            # 获取弹窗HTML
            html = self.driver.page_source
            comm_info = self.parse_communication_dialog(html)
            
            # 关闭弹窗
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".el-dialog__close, .el-dialog .el-button--default")
                if close_buttons:
                    self.driver.execute_script("arguments[0].click();", close_buttons[0])
                time.sleep(1)
            except:
                pass
                
            return comm_info
            
        except Exception as e:
            print(f"提取沟通记录失败: {e}")
            return {}
    
    def parse_edit_dialog(self, html):
        """解析编辑弹窗信息。"""
        try:
            soup = BeautifulSoup(html, "lxml")
        except:
            soup = BeautifulSoup(html, "html.parser")
            
        edit_info = {}
        dialog = soup.find("div", class_="el-dialog")
        
        if dialog:
            # 提取所有文本内容进行正则匹配
            html_text = dialog.get_text()
            
            # 定义所有可能的字段模式
            patterns = {
                "学生姓名": r"学生姓名[：:\s]*([^\s\n]+)",
                "高中": r"高中[：:\s]*([^\n]+?)(?=\s|专业类别|$|\n)",
                "专业类别": r"专业类别[：:\s]*([^\s\n]+)",
                "总分": r"总分[：:\s]*(\d+)",
                "语文分数": r"语文分数[：:\s]*(\d+)",
                "数学分数": r"数学分数[：:\s]*(\d+)",
                "外语分数": r"外语分数[：:\s]*(\d+)",
                "理综分数": r"理综分数[：:\s]*(\d+)",
                "文综分数": r"文综分数[：:\s]*(\d+)",
                "物理分数": r"物理分数[：:\s]*(\d+)",
                "化学分数": r"化学分数[：:\s]*(\d+)",
                "生物分数": r"生物分数[：:\s]*(\d+)",
                "历史分数": r"历史分数[：:\s]*(\d+)",
                "地理分数": r"地理分数[：:\s]*(\d+)",
                "政治分数": r"政治分数[：:\s]*(\d+)",
                "本人手机": r"本人手机[：:\s]*(\d+)",
                "家长手机": r"家长手机[：:\s]*(\d+)",
                "母亲手机": r"母亲手机[：:\s]*(\d+)",
                "父亲手机": r"父亲手机[：:\s]*(\d+)",
                "年份": r"年份[：:\s]*(\d{4})",
                "负责人": r"负责人[：:\s]*([^\s\n]+)",
                "报考强基计划院校": r"报考强基计划院校[：:\s]*([^\s\n]+)",
                "强基计划院校": r"强基计划院校[：:\s]*([^\s\n]+)",
                "再考专业": r"再考专业[：:\s]*([^\s\n]+)",
                "身份证号": r"身份证号[：:\s]*([^\s\n]+)",
                "考生号": r"考生号[：:\s]*([^\s\n]+)",
                "准考证号": r"准考证号[：:\s]*([^\s\n]+)",
                "邮箱": r"邮箱[：:\s]*([^\s\n]+)",
                "QQ": r"QQ[：:\s]*([^\s\n]+)",
                "微信": r"微信[：:\s]*([^\s\n]+)",
                "家庭住址": r"家庭住址[：:\s]*([^\n]+)",
                "民族": r"民族[：:\s]*([^\s\n]+)",
                "性别": r"性别[：:\s]*([^\s\n]+)",
                "出生日期": r"出生日期[：:\s]*([^\s\n]+)",
                "政治面貌": r"政治面貌[：:\s]*([^\s\n]+)",
                "特长": r"特长[：:\s]*([^\n]+)",
                "获奖情况": r"获奖情况[：:\s]*([^\n]+)",
                "备注": r"备注[：:\s]*([^\n]+)"
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, html_text)
                if match:
                    value = match.group(1).strip()
                    if value:
                        edit_info[field] = value
        
        return edit_info
    
    def parse_communication_dialog(self, html):
        """解析沟通记录弹窗信息。"""
        try:
            soup = BeautifulSoup(html, "lxml")
        except:
            soup = BeautifulSoup(html, "html.parser")
            
        comm_info = {}
        dialog = soup.find("div", class_="el-dialog")
        
        if dialog:
            html_text = dialog.get_text()
            
            # 提取沟通记录相关信息
            patterns = {
                "年份": r"年份[：:\s]*(\d{4})",
                "考生名称": r"考生名称[：:\s]*([^\s\n]+)",
                "高中": r"高中[：:\s]*([^\n]+?)(?=\s|$|\n)",
                "专业类别": r"专业类别[：:\s]*([^\s\n]+)",
                "总分": r"总分[：:\s]*(\d+)",
                "语文分数": r"语文分数[：:\s]*(\d+)",
                "数学分数": r"数学分数[：:\s]*(\d+)",
                "本人手机": r"本人手机[：:\s]*(\d+)",
                "家长手机": r"家长手机[：:\s]*(\d+)",
                "强基计划院校": r"强基计划院校[：:\s]*([^\s\n]+)",
                "承诺专业": r"承诺专业[：:\s]*([^\s\n]+)",
                "等级划分": r"等级划分[：:\s]*([^\s\n]+)",
                "沟通时间": r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
                "沟通内容": r"内容[：:\s]*([^\n]+)",
                "难点": r"难点[：:\s]*([^\n]+)"
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, html_text)
                if match:
                    value = match.group(1).strip()
                    if value:
                        comm_info[field] = value
        
        return comm_info
    
    def run_test(self):
        """运行测试。"""
        try:
            self.setup_driver()
            self.login()
            self.test_single_student_info_extraction()
        except Exception as e:
            print(f"测试过程出错: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    spider = SingleThreadRecruitSpider()
    spider.run_test() 