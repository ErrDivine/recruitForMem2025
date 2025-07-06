import time
import os
import json
import pickle
from datetime import datetime
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
import copy
from selenium.common.exceptions import TimeoutException, NoSuchElementException


URL = "https://recruit-student.tbs-datum.com/#/login?redirect=/student/studentIndex"
USERNAME = "HLJ1"
PASSWORD = "00000000"

# Query default filters
YEAR = "2025"  # 根据实际年份修改

# 根据实际登录页元素，修改以下三个选择器
USERNAME_SELECTOR = "//input[contains(@placeholder,'账号')]"  # XPath 或 CSS 选择器均可
PASSWORD_SELECTOR = "//input[contains(@placeholder,'密码')]"
LOGIN_BTN_SELECTOR = "//button[contains(., '登录')]"

# 配置参数
NUM_THREADS = 3  # 并发线程数量（建议不超过5，避免被网站限制）
MAX_RETRIES = 2  # 最大重试次数
THREAD_DELAY = 1  # 线程间延迟（秒）

# 测试模式配置
TEST_MODE = False  # 设置为True只处理前几个学生用于测试
TEST_STUDENTS_COUNT = 10  # 测试模式下处理的学生数量


class RecruitSpider:
    """使用 Selenium 登录招生网站并预留数据抓取接口。"""

    def __init__(self, headless: bool = True, driver_path: str | None = None, thread_id: int = 0):
        options = Options()
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        
        # 避免 Selenium 特征被检测
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 避免自动化检测
        options.add_argument("--disable-blink-features=AutomationControlled")
        # 增加稳定性参数
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        if thread_id > 0:  # 只有工作线程才设置独立端口和数据目录
            options.add_argument(f"--remote-debugging-port={9222 + thread_id}")
            options.add_argument(f"--user-data-dir=/tmp/chrome_profile_{thread_id}_{int(time.time())}")
        
        try:
            if driver_path:
                # 使用用户提供的本地 chromedriver
                self.driver = webdriver.Chrome(service=Service(driver_path), options=options)
            else:
                # 优先尝试系统自带 /usr/local/bin/chromedriver
                default_driver = "/usr/local/bin/chromedriver"
                if os.path.exists(default_driver):
                    self.driver = webdriver.Chrome(service=Service(default_driver), options=options)
                else:
                    # 回退到 webdriver_manager 自动下载（可能需要外网）
                    if thread_id == 0:  # 只在主线程打印一次
                        print("尝试在线下载 chromedriver，如果卡住或报错请手动下载并指定 driver_path …")
                    self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            raise RuntimeError(f"无法启动 Chrome 浏览器：{e}\n"
                             f"请确保已安装 Chrome 并下载对应版本的 chromedriver")
        
        self.driver.implicitly_wait(10)

        # 在新文档加载前注入脚本以隐藏 webdriver 痕迹
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            },
        )
        
        self.thread_id = thread_id

    def login(self):
        """打开网址并完成登录。"""
        self.driver.get(URL)
        print("打开登录页…")

        wait = WebDriverWait(self.driver, 20)

        # 等待账号输入框出现并填写
        username_input = wait.until(EC.presence_of_element_located((By.XPATH, USERNAME_SELECTOR)))
        username_input.clear()
        username_input.send_keys(USERNAME)

        # 等待密码框出现并填写
        password_input = wait.until(EC.presence_of_element_located((By.XPATH, PASSWORD_SELECTOR)))
        password_input.clear()
        password_input.send_keys(PASSWORD)

        # 等待登录按钮可点击
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, LOGIN_BTN_SELECTOR)))
        login_button.click()
        print("提交登录信息…")

        # 等待路由跳转至非 /login 页面
        try:
            WebDriverWait(self.driver, 15).until(lambda d: "/login" not in d.current_url)
            print("登录成功，当前页面：", self.driver.current_url)
        except Exception:
            print("登录后仍停留在登录页，可能账号/密码错误或被拦截，请检查。")

    def crawl(self):
        """登录后进入"考生信息"菜单并抓取表格。"""

        self.click_menu("考生信息")

        # 选择年份
        self.set_year(YEAR)

        # 点击搜索按钮以加载数据
        self.perform_search()

        # 等待表格数据行出现（element ui tbody tr）
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".el-table__body-wrapper tbody tr"))
        )

        # 收集所有学生的基础信息
        print("开始收集学生基础信息...")
        all_students = []
        page = 1
        expected_total = 244  # 已知总记录数
        
        while True:
            print(f"正在收集第{page}页的学生信息...")
            students = self.get_page_students(page)
            
            if not students:
                print(f"第{page}页没有学生信息，停止收集")
                break
                
            all_students.extend(students)
            print(f"第{page}页收集到 {len(students)} 名学生，总计 {len(all_students)} 名")
            
            # 检查是否已达到预期总数
            if len(all_students) >= expected_total:
                print(f"已收集到预期的 {expected_total} 名学生，停止收集")
                all_students = all_students[:expected_total]  # 确保不超过244条
                break
            
            # 测试模式：只处理指定数量的学生
            if TEST_MODE and len(all_students) >= TEST_STUDENTS_COUNT:
                all_students = all_students[:TEST_STUDENTS_COUNT]
                print(f"[测试模式] 只处理前 {TEST_STUDENTS_COUNT} 名学生")
                break
            
            # 检查是否还有下一页
            if not self.has_next_page():
                print("已到达最后一页")
                break
                
            self.next_page()
            page += 1
            time.sleep(1)  # 翻页间隔
        
        print(f"[主线程] 总共收集到 {len(all_students)} 名学生的基础信息")
        return all_students

    def process_single_student(self, student):
        """处理单个学生的详细信息。"""
        student_name = student.get('姓名', '未知')
        page_num = student.get('page_num', 1)
        row_index = student.get('row_index', 0)
        
        print(f"[线程-{self.thread_id}] 处理学生: {student_name} (第{page_num}页, 第{row_index+1}行)")
        
        for attempt in range(MAX_RETRIES):
            try:
                # 检查浏览器连接
                if not self.check_browser_alive():
                    print(f"[线程-{self.thread_id}] 浏览器连接断开，尝试重新连接...")
                    self.restart_browser(page_num)
                    continue
                
                # 确保在正确的页面和位置
                if not self.navigate_to_student_page(page_num):
                    print(f"[线程-{self.thread_id}] 无法导航到第{page_num}页")
                    continue
                
                # 获取编辑信息
                edit_info = self.get_edit_info(student_name, page_num, row_index)
                time.sleep(THREAD_DELAY)
                
                # 获取沟通记录
                communication_records = self.get_communication_records(row_index)
                
                # 合并所有信息
                student_full_info = {
                    **student,
                    'edit_info': edit_info,
                    'communication_records': communication_records,
                    'processed_time': datetime.now().isoformat(),
                    'thread_id': self.thread_id
                }
                
                print(f"[线程-{self.thread_id}] 成功处理学生: {student_name}")
                return student_full_info
                
            except Exception as e:
                print(f"[线程-{self.thread_id}] 处理学生 {student_name} 时出错 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)  # 重试前等待
                    continue
                else:
                    print(f"[线程-{self.thread_id}] 达到最大重试次数，返回基础信息")
                    return {**student, 'edit_info': {}, 'communication_records': [], 'error': str(e), 'thread_id': self.thread_id}
    
    def navigate_to_student_page(self, target_page):
        """导航到指定页面。"""
        try:
            # 检查当前是否在考生信息页面
            if "studentIndex" not in self.driver.current_url:
                self.click_menu("考生信息")
                self.set_year(YEAR)
                self.perform_search()
                time.sleep(2)
            
            # 获取当前页码
            current_page = self.get_current_page()
            
            # 如果已经在目标页面，直接返回
            if current_page == target_page:
                return True
            
            # 导航到目标页面
            if target_page == 1:
                # 回到第一页
                first_page_btn = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'number') and text()='1']")
                if first_page_btn:
                    first_page_btn[0].click()
                    time.sleep(2)
                    return True
            else:
                # 直接点击目标页码
                target_page_btn = self.driver.find_elements(By.XPATH, f"//button[contains(@class, 'number') and text()='{target_page}']")
                if target_page_btn:
                    target_page_btn[0].click()
                    time.sleep(2)
                    return True
                else:
                    # 如果目标页码不可见，逐页导航
                    while current_page < target_page:
                        if not self.go_to_next_page():
                            break
                        current_page += 1
                        time.sleep(1)
                    return current_page == target_page
            
            return False
            
        except Exception as e:
            print(f"[线程-{self.thread_id}] 导航到第{target_page}页失败: {e}")
            return False
    
    def get_current_page(self):
        """获取当前页码。"""
        try:
            active_page = self.driver.find_elements(By.CSS_SELECTOR, ".el-pagination .number.active")
            if active_page:
                return int(active_page[0].text)
            return 1
        except:
            return 1
    
    def check_browser_alive(self):
        """检查浏览器是否仍然可用。"""
        try:
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def restart_browser(self, target_page=1):
        """重启浏览器并重新登录。"""
        try:
            self.driver.quit()
        except:
            pass
        
        # 重新初始化浏览器
        self.__init__(headless=True, thread_id=self.thread_id)
        
        # 重新登录
        try:
            self.login()
            self.navigate_to_student_page(target_page)
        except Exception as e:
            print(f"[线程-{self.thread_id}] 重启浏览器失败: {e}")
    
    def go_to_next_page(self):
        """翻到下一页，返回是否成功。"""
        try:
            # 寻找下一页按钮
            next_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-next') or contains(text(), '下一页') or contains(., '>')]")
            
            for btn in next_buttons:
                if btn.is_enabled() and btn.is_displayed():
                    btn.click()
                    time.sleep(2)
                    return True
            
            # 也尝试页码按钮
            pagination_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".el-pagination .number")
            current_page = None
            
            for btn in pagination_buttons:
                if "active" in btn.get_text():
                    current_page = int(btn.text)
                    break
            
            if current_page:
                next_page_btn = self.driver.find_elements(By.XPATH, f"//button[contains(@class, 'number') and text()='{current_page + 1}']")
                if next_page_btn and next_page_btn[0].is_enabled():
                    next_page_btn[0].click()
                    time.sleep(2)
                    return True
            
            return False
            
        except Exception as e:
            print(f"翻页失败: {e}")
            return False

    def perform_search(self):
        """在考生信息页面点击搜索按钮。"""
        try:
            search_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '搜索')]]"))
            )
            search_btn.click()
            print("已点击搜索按钮，等待数据加载…")
        except Exception as e:
            print("未找到搜索按钮，跳过：", e)

    def set_year(self, year: str):
        """在年份日期选择器中输入年份，如 '2025'。"""
        try:
            year_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@role='combobox' and contains(@class,'el-date-editor') and @placeholder='']"))
            )
            year_input.click()
            # 清空后输入年份，回车
            year_input.send_keys(Keys.CONTROL, "a")
            year_input.send_keys(year)
            year_input.send_keys(Keys.ENTER)
            print(f"已选择年份：{year}")
            time.sleep(0.5)
        except Exception as e:
            print("选择年份失败：", e)

    # ---------------------------------------------------------------------
    # 辅助方法
    # ---------------------------------------------------------------------

    def click_menu(self, menu_text: str):
        """在侧边栏点击指定菜单文字。如果已是激活状态则跳过。"""
        xpath = f"//li[span[contains(., '{menu_text}')]]"
        wait = WebDriverWait(self.driver, 15)
        menu_li = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        # 若元素已含 is-active 类则无需点击
        if "is-active" not in menu_li.get_attribute("class"):
            menu_li.click()

    def parse_table_basic_info(self, html: str):
        """解析表格基础信息。"""
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            # 若系统未安装 lxml，则退回自带的 html.parser
            soup = BeautifulSoup(html, "html.parser")
        
        students = []
        
        # 查找表格体
        tbody = soup.find("tbody")
        if not tbody:
            print("未找到表格体，可能页面尚未加载完成")
            return students
        
        rows = tbody.find_all("tr")
        print(f"找到 {len(rows)} 行数据")
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 10:  # 确保有足够的列
                student = {
                    "姓名": cells[0].get_text(strip=True),
                    "学校": cells[1].get_text(strip=True), 
                    "专业类别": cells[2].get_text(strip=True),
                    "总分": cells[3].get_text(strip=True),
                    "排名": cells[4].get_text(strip=True),
                    "负责人": cells[5].get_text(strip=True),
                    "录取专业": cells[6].get_text(strip=True),
                    "意向专业": cells[7].get_text(strip=True),
                    "承诺专业": cells[8].get_text(strip=True),
                    "满足承诺": cells[9].get_text(strip=True),
                    "等级划分": cells[10].get_text(strip=True) if len(cells) > 10 else "",
                    "沟通时间": cells[11].get_text(strip=True) if len(cells) > 11 else "",
                    "内容": cells[12].get_text(strip=True) if len(cells) > 12 else ""
                }
                students.append(student)
        
        return students

    def get_edit_info(self, student_name, page_num, row_index):
        """获取编辑弹窗中的详细信息。"""
        print(f"[DEBUG] 开始获取 {student_name} 的编辑信息")
        
        try:
            # 重新导航到学生列表页面
            if page_num > 1:
                self.navigate_to_page(page_num)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
            time.sleep(1)
            
            # 更精确地定位编辑按钮
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            print(f"[DEBUG] 找到 {len(rows)} 行数据")
            
            edit_button = None
            for i, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) > 0:
                    row_student_name = cells[0].text.strip()
                    print(f"[DEBUG] 第{i}行学生姓名: {row_student_name}")
                    
                    if row_student_name == student_name:
                        # 在这一行中查找编辑按钮
                        edit_buttons = row.find_elements(By.CSS_SELECTOR, "button")
                        for btn in edit_buttons:
                            if "编辑" in btn.text or "edit" in btn.get_attribute("class").lower():
                                edit_button = btn
                                print(f"[DEBUG] 找到编辑按钮: {btn.text}")
                                break
                        break
             
            if not edit_button:
                print(f"[DEBUG] 未找到 {student_name} 的编辑按钮")
                return {}
             
            print(f"[DEBUG] 点击编辑按钮")
            # 点击编辑按钮
            self.driver.execute_script("arguments[0].click();", edit_button)
             
            # 等待编辑弹窗出现（增加等待时间）
            print(f"[DEBUG] 等待编辑弹窗出现")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".el-dialog")))
            time.sleep(2)
             
            print(f"[DEBUG] 获取弹窗HTML")
            # 获取弹窗HTML并解析
            html = self.driver.page_source
            edit_info = self.parse_edit_dialog(html)
             
            print(f"[DEBUG] 解析到编辑信息: {edit_info}")
            
            # 关闭弹窗
            try:
                close_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".el-dialog__close, .el-dialog .el-button--default")
                if close_buttons:
                    self.driver.execute_script("arguments[0].click();", close_buttons[0])
                else:
                    # 尝试按ESC键关闭
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except Exception as e:
                print(f"[DEBUG] 关闭编辑弹窗失败: {e}")
                # 尝试其他方式关闭
                try:
                    close_button = self.driver.find_element(By.CSS_SELECTOR, ".el-dialog__header .el-dialog__headerbtn")
                    self.driver.execute_script("arguments[0].click();", close_button)
                    time.sleep(1)
                except Exception as e:
                    print(f"[DEBUG] 尝试其他方式关闭弹窗也失败: {e}")
            
            return edit_info
             
        except Exception as e:
            print(f"[DEBUG] 获取 {student_name} 编辑信息时出错: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_communication_records(self, row_index: int):
        """点击第 row_index 行的沟通记录按钮获取记录。"""
        try:
            # 等待页面稳定
            time.sleep(1)
            
            # 找到沟通记录按钮并点击
            comm_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '沟通记录')]")
            if row_index < len(comm_buttons):
                # 滚动到按钮位置
                self.driver.execute_script("arguments[0].scrollIntoView(true);", comm_buttons[row_index])
                time.sleep(0.5)
                
                # 点击按钮
                self.driver.execute_script("arguments[0].click();", comm_buttons[row_index])
                
                # 等待沟通记录弹窗出现
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".el-dialog"))
                )
                
                # 获取弹窗内容
                dialog_html = self.driver.page_source
                comm_records = self.parse_communication_dialog(dialog_html)
                
                # 关闭弹窗
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, ".el-dialog__close, .el-dialog__headerbtn")
                if close_btns:
                    close_btns[0].click()
                else:
                    # 尝试按ESC键关闭
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                
                # 等待弹窗关闭
                time.sleep(1)
                WebDriverWait(self.driver, 10).until_not(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".el-dialog"))
                )
                
                return comm_records
                
        except Exception as e:
            print(f"获取沟通记录失败（第{row_index}行）：{e}")
            return []
        
        return []

    def parse_edit_dialog(self, html: str):
        """解析编辑弹窗中的详细信息。"""
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        
        edit_info = {}
        
        # 查找弹窗中的所有输入字段
        dialog = soup.find("div", class_="el-dialog")
        if dialog:
            # 添加调试信息
            print(f"[DEBUG] 正在解析编辑弹窗，HTML长度: {len(html)}")
            
            # 查找所有表单项
            form_items = dialog.find_all("div", class_="el-form-item")
            print(f"[DEBUG] 找到 {len(form_items)} 个表单项")
            
            for item in form_items:
                label_elem = item.find("label", class_="el-form-item__label")
                if label_elem:
                    label = label_elem.get_text(strip=True).rstrip("：*:")
                    print(f"[DEBUG] 处理标签: {label}")
                    
                    # 获取表单项内容区域
                    content_elem = item.find("div", class_="el-form-item__content")
                    if content_elem:
                        value = self.extract_form_value(content_elem, label)
                        if value:
                            edit_info[label] = value
                            print(f"[DEBUG] 提取到值: {label} = {value}")
                        else:
                            print(f"[DEBUG] 未能提取值: {label}")
            
            # 特殊处理：直接从HTML文本中提取关键信息
            html_text = dialog.get_text()
            
            # 使用正则表达式提取特定字段
            patterns = {
                "年份": r"年份[：:\s]*(\d{4})",
                "考生名称": r"考生名称[：:\s]*([^\s\n]+)",
                "高中": r"高中[：:\s]*([^\n]+?)(?=\s|$|\n)",
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
                if field not in edit_info:  # 只有当字段还未提取到时才使用正则
                    match = re.search(pattern, html_text)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            edit_info[field] = value
                            print(f"[DEBUG] 正则提取到: {field} = {value}")
            
            # 特殊处理开关状态
            switches = {
                "是否服从调剂": "是否服从调剂",
                "是否报考强基计划": "是否报考强基计划"
            }
            
            for switch_name, field_name in switches.items():
                if field_name not in edit_info:
                    # 查找开关状态
                    switch_elem = dialog.find(string=lambda text: text and switch_name in text)
                    if switch_elem:
                        parent = switch_elem.find_parent()
                        if parent:
                            switch_control = parent.find_next("span", class_="el-switch")
                            if switch_control:
                                if "is-checked" in switch_control.get("class", []):
                                    edit_info[field_name] = "是"
                                else:
                                    edit_info[field_name] = "否"
                                print(f"[DEBUG] 开关状态提取: {field_name} = {edit_info[field_name]}")
            
            # 特殊处理意向专业表格（如截图中显示的专业组表格）
            major_table = dialog.find("table")
            if major_table:
                edit_info["意向专业详情"] = self.parse_major_preference_table(major_table)
                print(f"[DEBUG] 提取到意向专业表格")
        else:
            print(f"[DEBUG] 未找到编辑弹窗")
        
        return edit_info

    def extract_form_value(self, content_elem, label):
        """从表单内容元素中提取值。"""
        # 尝试不同类型的表单控件
        
        # 1. 输入框
        input_elem = content_elem.find("input")
        if input_elem:
            value = input_elem.get("value")
            if value and value.strip():
                return value.strip()
            # 有些输入框的值可能在placeholder中
            placeholder = input_elem.get("placeholder")
            if placeholder and placeholder not in ["请输入", "请选择"]:
                return placeholder.strip()
        
        # 2. Element UI 选择器
        select_input = content_elem.find("input", class_="el-input__inner")
        if select_input:
            value = select_input.get("value")
            if value and value.strip():
                return value.strip()
        
        # 3. 下拉选择框显示的文本
        select_span = content_elem.find("span", class_="el-input__suffix")
        if select_span:
            # 查找同级的显示文本
            display_elem = content_elem.find("input", readonly=True)
            if display_elem:
                value = display_elem.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 4. 开关/切换按钮
        switch_elem = content_elem.find("span", class_="el-switch")
        if switch_elem:
            if "is-checked" in switch_elem.get("class", []):
                return "是"
            else:
                return "否"
        
        # 5. 复选框
        checkbox = content_elem.find("input", {"type": "checkbox"})
        if checkbox:
            if checkbox.get("checked") or "checked" in checkbox.get("class", []):
                return "是"
            else:
                return "否"
        
        # 6. 多选标签
        tags = content_elem.find_all("span", class_="el-tag")
        if tags:
            tag_values = []
            for tag in tags:
                tag_text = tag.get_text(strip=True)
                if tag_text and tag_text not in ["×"]:  # 排除删除按钮
                    tag_values.append(tag_text)
            if tag_values:
                return "; ".join(tag_values)
        
        # 7. 数字输入框（加减按钮形式）
        number_input = content_elem.find("div", class_="el-input-number")
        if number_input:
            num_input = number_input.find("input")
            if num_input:
                value = num_input.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 8. 文本域
        textarea = content_elem.find("textarea")
        if textarea:
            value = textarea.get_text(strip=True) or textarea.get("value", "")
            if value and value.strip():
                return value.strip()
        
        # 9. 级联选择器
        cascader = content_elem.find("div", class_="el-cascader")
        if cascader:
            cascader_input = cascader.find("input")
            if cascader_input:
                value = cascader_input.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 10. 日期选择器
        date_picker = content_elem.find("div", class_="el-date-editor")
        if date_picker:
            date_input = date_picker.find("input")
            if date_input:
                value = date_input.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 11. 时间选择器  
        time_picker = content_elem.find("div", class_="el-time-picker")
        if time_picker:
            time_input = time_picker.find("input")
            if time_input:
                value = time_input.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 12. 评分组件
        rate = content_elem.find("div", class_="el-rate")
        if rate:
            stars = rate.find_all("i", class_="el-rate__icon")
            active_stars = [star for star in stars if "el-rate__icon--active" in star.get("class", [])]
            if active_stars:
                return str(len(active_stars))
        
        # 13. 滑块
        slider = content_elem.find("div", class_="el-slider")
        if slider:
            slider_input = slider.find("input", {"type": "hidden"})
            if slider_input:
                value = slider_input.get("value")
                if value and value.strip():
                    return value.strip()
        
        # 14. 单选按钮组
        radio_group = content_elem.find("div", class_="el-radio-group")
        if radio_group:
            checked_radio = radio_group.find("input", {"checked": True}) or radio_group.find("input", class_="el-radio__original")
            if checked_radio:
                radio_label = checked_radio.find_next("span", class_="el-radio__label")
                if radio_label:
                    return radio_label.get_text(strip=True)
        
        # 15. 多选框组
        checkbox_group = content_elem.find("div", class_="el-checkbox-group")
        if checkbox_group:
            checked_boxes = checkbox_group.find_all("input", {"checked": True})
            if checked_boxes:
                labels = []
                for box in checked_boxes:
                    label = box.find_next("span", class_="el-checkbox__label")
                    if label:
                        labels.append(label.get_text(strip=True))
                if labels:
                    return "; ".join(labels)
        
        # 16. 颜色选择器
        color_picker = content_elem.find("div", class_="el-color-picker")
        if color_picker:
            color_trigger = color_picker.find("span", class_="el-color-picker__trigger")
            if color_trigger:
                style = color_trigger.get("style", "")
                if "background-color" in style:
                    return style.split("background-color:")[1].split(";")[0].strip()
        
        # 9. 纯文本内容（但要排除一些无用文本）
        text = content_elem.get_text(strip=True)
        if text and text != label and len(text) > 0:
            # 排除一些无意义的文本
            exclude_texts = ["请选择", "请输入", "选择", "输入", "", "可拖拽目标专业组或专业进行排序"]
            if text not in exclude_texts and not text.startswith("请选择") and not text.startswith("请输入"):
                # 如果文本太长，可能包含多个值，尝试清理
                if len(text) > 100:
                    # 可能是包含多个元素的复合文本，尝试提取有用部分
                    lines = text.split('\n')
                    useful_lines = [line.strip() for line in lines if line.strip() and line.strip() not in exclude_texts]
                    if useful_lines:
                        return "; ".join(useful_lines[:3])  # 只取前3行有用信息
                else:
                    return text
        
        return None
    
    def parse_major_preference_table(self, table):
        """解析意向专业表格。"""
        preferences = []
        
        rows = table.find_all("tr")
        for row in rows[1:]:  # 跳过表头
            cells = row.find_all("td")
            if len(cells) >= 3:
                pref = {
                    "专业组": cells[0].get_text(strip=True),
                    "专业代码": cells[1].get_text(strip=True),
                    "专业名称": cells[2].get_text(strip=True)
                }
                preferences.append(pref)
        
        return preferences

    def parse_communication_dialog(self, html: str):
        """解析沟通记录弹窗中的记录列表。"""
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        
        communication_info = {}
        
        # 查找弹窗中的沟通记录
        dialog = soup.find("div", class_="el-dialog")
        if dialog:
            # 1. 提取考生基础信息部分（左侧信息区域）
            # 查找包含考生信息的区域
            info_sections = dialog.find_all("div", string=lambda text: text and "考生信息" in text)
            if not info_sections:
                # 尝试查找包含年份、考生名称等信息的区域
                info_container = dialog.find("div", string=lambda text: text and "年份" in text)
                if info_container:
                    communication_info.update(self.parse_student_basic_info_from_text(info_container.get_text()))
            else:
                for section in info_sections:
                    parent = section.find_parent()
                    if parent:
                        communication_info.update(self.parse_student_basic_info_from_text(parent.get_text()))
            
            # 2. 提取右侧的专业和等级信息
            # 承诺专业
            commitment_labels = dialog.find_all(string=lambda text: text and "承诺专业" in text)
            for label in commitment_labels:
                parent = label.find_parent()
                if parent:
                    # 查找相邻的选择框或输入框
                    select_elem = parent.find_next("select") or parent.find_next("input", class_="el-input__inner")
                    if select_elem:
                        value = select_elem.get("value") or select_elem.get_text(strip=True)
                        if value and value.strip():
                            communication_info["承诺专业"] = value.strip()
                        break
            
            # 等级划分
            level_labels = dialog.find_all(string=lambda text: text and "等级划分" in text)
            for label in level_labels:
                parent = label.find_parent()
                if parent:
                    select_elem = parent.find_next("select") or parent.find_next("input", class_="el-input__inner")
                    if select_elem:
                        value = select_elem.get("value") or select_elem.get_text(strip=True)
                        if value and value.strip():
                            communication_info["等级划分"] = value.strip()
                        break
            
            # 3. 提取沟通时间
            time_labels = dialog.find_all(string=lambda text: text and "沟通时间" in text)
            for label in time_labels:
                parent = label.find_parent()
                if parent:
                    time_input = parent.find_next("input")
                    if time_input:
                        value = time_input.get("value")
                        if value and value.strip():
                            communication_info["沟通时间"] = value.strip()
                        break
            
            # 也可以通过特定的时间格式匹配
            if "沟通时间" not in communication_info:
                import re
                time_pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
                time_match = re.search(time_pattern, dialog.get_text())
                if time_match:
                    communication_info["沟通时间"] = time_match.group(1)
            
            # 4. 提取沟通内容和难点
            textareas = dialog.find_all("textarea")
            
            # 查找内容标签
            content_labels = dialog.find_all(string=lambda text: text and "内容" in text and "沟通" not in text)
            if content_labels and len(textareas) > 0:
                # 第一个文本域通常是内容
                content_text = textareas[0].get_text(strip=True) or textareas[0].get("value", "")
                if content_text:
                    communication_info["沟通内容"] = content_text
            
            # 查找难点标签
            difficulty_labels = dialog.find_all(string=lambda text: text and "难点" in text)
            if difficulty_labels and len(textareas) > 1:
                # 第二个文本域通常是难点
                difficulty_text = textareas[1].get_text(strip=True) or textareas[1].get("value", "")
                if difficulty_text:
                    communication_info["难点"] = difficulty_text
            elif difficulty_labels and len(textareas) == 1:
                # 如果只有一个文本域，检查是否是难点
                for label in difficulty_labels:
                    parent = label.find_parent()
                    if parent:
                        textarea = parent.find_next("textarea")
                        if textarea:
                            difficulty_text = textarea.get_text(strip=True) or textarea.get("value", "")
                            if difficulty_text:
                                communication_info["难点"] = difficulty_text
                            break
            
            # 5. 如果以上方法没有提取到内容，尝试更通用的方法
            if "沟通内容" not in communication_info and "难点" not in communication_info:
                all_text = dialog.get_text()
                
                # 查找包含具体沟通内容的文本段
                lines = all_text.split('\n')
                content_started = False
                content_lines = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 如果是时间格式的行，可能是沟通记录的开始
                    if re.match(r'\d{4}-\d{2}-\d{2}', line) or "内容" in line:
                        content_started = True
                        continue
                    
                    if content_started and line and len(line) > 10:  # 跳过太短的行
                        # 排除一些系统文本
                        if not any(skip in line for skip in ["保存", "取消", "请选择", "请输入"]):
                            content_lines.append(line)
                
                if content_lines:
                    communication_info["沟通内容"] = "\n".join(content_lines[:5])  # 取前5行内容
        
        return communication_info
    
    def parse_student_basic_info_from_text(self, text):
        """从文本中解析学生基础信息。"""
        info = {}
        
        # 使用正则表达式提取信息
        import re
        
        # 定义字段模式
        patterns = {
            "年份": r"年份[：:\s]*(\d{4})",
            "考生名称": r"考生名称[：:\s]*([^\s\n]+)",
            "高中": r"高中[：:\s]*([^\n]+?)(?=\s|$|\n)",
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
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                if value:
                    info[field] = value
        
        return info

    def close(self):
        """关闭浏览器驱动。"""
        try:
            self.driver.quit()
        except:
            pass

    def get_total_records_count(self, html):
        """从页面HTML中提取总记录数。"""
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
        
        # 查找显示总数的元素，通常在分页组件中
        # 可能的文本模式："共 243 条"、"共243条"、"总计 243 条"等
        total_patterns = [
            r'共\s*(\d+)\s*条',
            r'总计\s*(\d+)\s*条',
            r'Total:\s*(\d+)',
            r'(\d+)\s*条记录'
        ]
        
        page_text = soup.get_text()
        
        for pattern in total_patterns:
            match = re.search(pattern, page_text)
            if match:
                total_count = int(match.group(1))
                return total_count
        
        return 0

    def get_page_students(self, page):
        """获取当前页的学生信息。"""
        try:
            html = self.driver.page_source
            students = self.parse_table_basic_info(html)
            
            # 为每个学生添加页面信息
            for i, student in enumerate(students):
                student['page_num'] = page
                student['row_index'] = i
                
            return students
        except Exception as e:
            print(f"获取第{page}页学生信息时出错: {e}")
            return []
    
    def has_next_page(self):
        """检查是否有下一页。"""
        try:
            # 查找下一页按钮
            next_button = self.driver.find_element(By.CSS_SELECTOR, ".el-pagination .btn-next")
            return not next_button.get_attribute("disabled")
        except:
            return False
    
    def next_page(self):
        """翻到下一页。"""
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, ".el-pagination .btn-next")
            if not next_button.get_attribute("disabled"):
                next_button.click()
                time.sleep(2)  # 等待页面加载
                return True
            return False
        except Exception as e:
            print(f"翻页失败: {e}")
            return False

    def navigate_to_page(self, page_num):
        """导航到指定页面。"""
        try:
            current_page = 1
            while current_page < page_num:
                if not self.next_page():
                    break
                current_page += 1
            return current_page == page_num
        except Exception as e:
            print(f"导航到第{page_num}页失败: {e}")
            return False

    def start_detail_processing_threads(self, all_students):
        """启动多线程处理详细信息。"""
        print(f"[主线程] 启动 {NUM_THREADS} 个工作线程处理详细信息...")

def worker_thread(student_queue, result_queue, thread_id):
    """工作线程函数。"""
    spider = None
    try:
        # 创建线程独立的爬虫实例
        spider = RecruitSpider(headless=True, thread_id=thread_id)
        spider.login()
        
        while True:
            try:
                # 从队列获取学生信息
                student = student_queue.get(timeout=5)
                if student is None:  # 结束信号
                    break
                
                # 处理学生详细信息
                result = spider.process_single_student(student)
                result_queue.put(result)
                
                student_queue.task_done()
                
            except Empty:
                break
            except Exception as e:
                print(f"[线程-{thread_id}] 工作线程错误: {e}")
                student_queue.task_done()
                
    except Exception as e:
        print(f"[线程-{thread_id}] 线程初始化失败: {e}")
    finally:
        if spider:
            spider.close()

def crawl_with_multithreading():
    """使用多线程爬取所有学生信息。"""
    print(f"开始多线程爬取，使用 {NUM_THREADS} 个线程...")
    
    # 主线程：收集所有学生基础信息
    main_spider = RecruitSpider(headless=True, thread_id=0)
    try:
        main_spider.login()
        all_students_basic = main_spider.crawl()
        
        if not all_students_basic:
            print("未获取到学生基础信息")
            return
        
        print(f"开始多线程处理 {len(all_students_basic)} 名学生的详细信息...")
        
        # 创建队列
        student_queue = Queue()
        result_queue = Queue()
        
        # 将学生信息放入队列
        for student in all_students_basic:
            student_queue.put(student)
        
        # 启动工作线程
        threads = []
        for i in range(NUM_THREADS):
            t = threading.Thread(target=worker_thread, args=(student_queue, result_queue, i+1))
            t.start()
            threads.append(t)
            time.sleep(1)  # 错开线程启动时间
        
        # 收集结果
        all_results = []
        processed_count = 0
        
        while processed_count < len(all_students_basic):
            try:
                result = result_queue.get(timeout=30)
                all_results.append(result)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    print(f"已处理 {processed_count}/{len(all_students_basic)} 名学生")
                    
            except Empty:
                print("等待结果超时，检查线程状态...")
                # 检查是否有线程还在工作
                active_threads = [t for t in threads if t.is_alive()]
                if not active_threads:
                    print("所有工作线程已结束")
                    break
        
        # 发送结束信号
        for _ in range(NUM_THREADS):
            student_queue.put(None)
        
        # 等待所有线程结束
        for t in threads:
            t.join(timeout=10)
        
        # 保存结果
        if all_results:
            save_students_data(all_results)
            print(f"多线程爬取完成！总共处理了 {len(all_results)} 名学生")
        else:
            print("未获取到任何学生详细信息")
            
    except Exception as e:
        print(f"多线程爬取过程出错: {e}")
    finally:
        main_spider.close()

def save_students_data(students_data):
    """保存完整的学生数据到文件。"""
    if not students_data:
        print("没有学生数据需要保存")
        return
    
    # 添加时间戳到文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存为 JSON 格式（包含完整结构化数据）
    json_filename = f"students_full_info_{timestamp}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(students_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存基础信息为 CSV（便于查看）
    basic_data = []
    for student in students_data:
        basic_info = {k: v for k, v in student.items() if k not in ['edit_info', 'communication_records', 'page_num', 'row_index', 'global_index', 'thread_id', 'processed_time']}
        basic_data.append(basic_info)
    
    csv_filename = f"students_basic_info_{timestamp}.csv"
    df = pd.DataFrame(basic_data)
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    
    print(f"已保存完整学生信息:")
    print(f"  - {json_filename}: {len(students_data)} 名学生的完整信息")
    print(f"  - {csv_filename}: {len(students_data)} 名学生的基础信息")

if __name__ == "__main__":
    try:
        crawl_with_multithreading()
    except KeyboardInterrupt:
        print("用户中断程序")
    except Exception as e:
        print(f"程序出现错误: {e}")
