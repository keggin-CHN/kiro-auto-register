import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from faker import Faker
import random
import time
import json
import os
from datetime import datetime
from config import HEADLESS, SLOW_MO, BROWSER_TYPE
from services.email_service import create_temp_email, wait_for_verification_email, ChatGPTMailClient
from selenium.webdriver.common.action_chains import ActionChains
from helpers.multilang import lang_selector
from helpers.browser_factory import create_driver as factory_create_driver, cleanup_driver
from services.kiro_oauth import perform_kiro_oauth_in_browser, KiroOAuthClient
from services.aws_sso_oidc import perform_aws_sso_oidc_auto

# 截图保存目录 (src 目录)
SCREENSHOT_DIR = str(Path(__file__).parent.parent)

fake = Faker('en_US')


def generate_strong_password():
    """生成高强度密码"""
    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choices(chars, k=16))
    # 确保包含大小写、数字和特殊字符
    password = random.choice(string.ascii_uppercase) + random.choice(string.ascii_lowercase) + \
               random.choice(string.digits) + random.choice("!@#$%^&*") + password[4:]
    return password


def save_account(email, password, name, jwt_token="", kiro_token=None, aws_sso_token=None):
    """保存账号信息到文件 (使用格式化 JSON 数组)"""
    account_info = {
        "email": email,
        "password": password,
        "name": name,
        "jwt_token": jwt_token,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "registered"
    }
    
    # 添加 Kiro token 信息
    if kiro_token:
        account_info["kiro_access_token"] = kiro_token.get("access_token", "")
        account_info["kiro_csrf_token"] = kiro_token.get("csrf_token", "")
        account_info["kiro_refresh_token"] = kiro_token.get("refresh_token", "")
        account_info["kiro_expires_in"] = kiro_token.get("expires_in", 0)
        account_info["kiro_profile_arn"] = kiro_token.get("profile_arn", "")
        account_info["status"] = "kiro_authorized"
    
    # 添加 AWS SSO OIDC token 信息 (用于 Kiro Account Manager 导入)
    if aws_sso_token:
        account_info["aws_sso_refresh_token"] = aws_sso_token.get("refresh_token", "")  # aor开头
        account_info["aws_sso_client_id"] = aws_sso_token.get("client_id", "")
        account_info["aws_sso_client_secret"] = aws_sso_token.get("client_secret", "")
        account_info["aws_sso_access_token"] = aws_sso_token.get("access_token", "")
        account_info["aws_sso_region"] = aws_sso_token.get("region", "us-east-1")
        account_info["aws_sso_provider"] = aws_sso_token.get("provider", "BuilderId")
        account_info["status"] = "aws_sso_authorized"
    
    file_path = "accounts.json"
    
    try:
        # 读取现有账号
        accounts = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                accounts = json.load(f)
        
        # 添加新账号
        accounts.append(account_info)
        
        # 写入格式化 JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 账号已保存: {email}")
    except Exception as e:
        print(f"❌ 保存账号失败: {e}")


def save_account_info(email, password, name, jwt_token):
    """保存账号信息到文件"""
    accounts_file = "accounts.json"
    accounts = []

    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding='utf-8') as f:
            accounts = json.load(f)

    account = {
        "email": email,
        "password": password,
        "name": name,
        "jwt_token": jwt_token,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active"
    }
    accounts.append(account)

    with open(accounts_file, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)

    print(f"账号信息已保存到 {accounts_file}")


def human_delay(min_sec=0.5, max_sec=2.0):
    """模拟人类操作的随机延迟"""
    # 增加随机性，有时候会有更长的停顿 (模拟思考)
    if random.random() < 0.15:  # 15% 概率有更长停顿
        time.sleep(random.uniform(2.5, 5.0))
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(element, text):
    """模拟人类打字，速度随机波动"""
    # 基础打字速度因子 (0.8 ~ 1.2)，模拟每个人打字速度不同
    speed_factor = random.uniform(0.7, 1.3)
    
    for char in text:
        element.send_keys(char)
        # 基础延迟 + 随机波动
        delay = random.uniform(0.04, 0.15) * speed_factor
        
        # 模拟偶尔的停顿 (打字间隙)
        if random.random() < 0.05:
            delay += random.uniform(0.2, 0.5)
            
        time.sleep(delay)


def human_click(driver, element):
    """模拟人类鼠标点击"""
    try:
        # 1. 移动到元素位置 (带一点随机偏移)
        action = ActionChains(driver)
        # 偏移不需要太大，元素中心附近即可
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        
        action.move_to_element_with_offset(element, offset_x, offset_y)
        action.perform()
        
        # 2. 悬停一下 (思考时间)
        time.sleep(random.uniform(0.1, 0.4))
        
        # 3. 点击 (模拟按下和松开的微小间隔)
        action.click_and_hold().pause(random.uniform(0.05, 0.15)).release().perform()
        
    except Exception as e:
        # 如果 ActionChains 失败，回退到普通点击
        print(f"⚠️ 鼠标模拟失败，回退到普通点击: {e}")
        try:
            element.click()
        except:
            driver.execute_script("arguments[0].click();", element)


def run(fixed_account=None):
    # 导入配置和工具
    import os
    from config import REGION_CURRENT, DEVICE_TYPE
    from helpers.utils import (
        get_user_agent_for_region, get_locale_for_region,
        get_timezone_for_region, get_accept_language_for_region, is_mobile
    )
    from services.outlook_service import get_verification_code_from_outlook
    from managers.proxy_manager import proxy_manager
    
    # === 使用智能识别的地区（如果有）===
    detected_region = os.environ.get('AUTO_REGION', REGION_CURRENT)
    
    # 更新多语言选择器到正确的地区
    lang_selector.update_region(detected_region)
    
    # 显示当前环境设置（使用检测到的地区）
    device_emoji = "📱" if is_mobile() else "💻"
    print(f"\n{device_emoji} === 当前环境设置 ===")
    print(f"📍 地区: {detected_region.upper()}")
    print(f"🖥️  设备: {DEVICE_TYPE.upper()}")
    print(f"🌐 语言: {get_locale_for_region(detected_region)}")
    print(f"🕐 时区: {get_timezone_for_region(detected_region)}")
    lang_selector.print_current_language()
    proxy_manager.print_proxy_info()
    print("=" * 50)
    
    # 获取代理（如果启用）- 带测试验证
    proxy_url = None
    if proxy_manager.use_proxy:
        max_proxy_attempts = 3
        for proxy_attempt in range(max_proxy_attempts):
            proxy_url = proxy_manager.get_proxy()
            if not proxy_url:
                print("⚠️  代理获取失败")
                continue
            
            # 测试代理是否可用
            print("🔍 测试代理连接...")
            try:
                import requests
                proxies = {'http': proxy_url, 'https': proxy_url}
                test_resp = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
                if test_resp.status_code == 200:
                    print(f"✅ 代理测试通过，出口IP: {test_resp.json().get('origin', 'Unknown')}")
                    break
                else:
                    print(f"⚠️  代理测试失败 (HTTP {test_resp.status_code})，重试...")
                    proxy_url = None
            except Exception as e:
                print(f"⚠️  代理测试失败: {e}，重试...")
                proxy_url = None
        
        if not proxy_url:
            print("❌ 所有代理尝试失败，退出运行")
            print("=" * 50)
            return  # 直接退出，不允许无代理运行
        print("=" * 50)
    
    # 第一步：准备邮箱
    if fixed_account:
        # 使用 Outlook (fixed_account 包含完整的 credentials)
        email_address = fixed_account['email']
        jwt_token = "OUTLOOK_API" 
        print(f"📧 使用固定 Outlook 邮箱: {email_address}")
    else:
        # 使用临时邮箱
        print("📧 点击创建临时邮箱...")
        email_address, jwt_token = create_temp_email()
        email_api_url = None
    
    if not email_address:
        print("创建邮箱失败，退出")
        return

    # 获取地区相关参数
    user_agent = get_user_agent_for_region(detected_region)
    locale = get_locale_for_region(detected_region)
    accept_language = get_accept_language_for_region(detected_region)
    
    print(f"User-Agent: {user_agent[:80]}...")
    print(f"🌐 浏览器类型: {BROWSER_TYPE.upper()}")
    
    # 使用浏览器工厂创建驱动
    print("\n正在启动浏览器...")
    driver = None
    try:
        driver = factory_create_driver(
            proxy_url=proxy_url,
            user_agent=user_agent,
            locale=locale,
            accept_language=accept_language
        )
        wait = WebDriverWait(driver, 30)
        
    except Exception as e:
        print(f"❌ 浏览器启动失败: {e}")
        return

    # 设置时区（使用检测到的地区）- 仅对支持 CDP 的浏览器有效
    try:
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
            'timezoneId': get_timezone_for_region(detected_region)
        })
        print(f"时区已设置为: {get_timezone_for_region(detected_region)}")
    except Exception as e:
        print(f"设置时区失败（非关键，Edge 可能不支持）: {e}")
    
    # 设置地理位置权限（使用检测到的地区）
    try:
        # 各地区的大致坐标
        geo_locations = {
            'germany': {'latitude': 52.52, 'longitude': 13.405, 'accuracy': 100},
            'japan': {'latitude': 35.6762, 'longitude': 139.6503, 'accuracy': 100},
            'usa': {'latitude': 40.7128, 'longitude': -74.0060, 'accuracy': 100}
        }
        location = geo_locations.get(detected_region, geo_locations['usa'])
        driver.execute_cdp_cmd('Emulation.setGeolocationOverride', location)
        print(f"地理位置已设置")
    except Exception as e:
        print(f"设置地理位置失败（非关键，Edge 可能不支持）: {e}")

    try:
        # 第二步：打开 AWS Builder 页面
        print("\n正在打开 AWS Builder 页面...")
        driver.get("https://builder.aws.com/start")
        human_delay(2, 3)
        print(f"页面标题: {driver.title}")

        # 处理Cookie弹窗（必须先关闭，否则会遮挡元素）
        print("检查Cookie弹窗...")
        human_delay(3, 4)  # 给足够时间让弹窗完全加载
        
        cookie_closed = False
        
        # 尝试多种方法关闭Cookie弹窗
        try:
            # 方法1: 直接查找Accept按钮（最常见）
            accept_selectors = [
                "//button[text()='Accept']",
                "//button[contains(text(), 'Accept')]",
                "//button[@id='awsccc-cb-btn-accept']",
                "//button[contains(@class, 'awsccc')]",
                "//div[@id='awsccc-cs-modalcontent']//button[1]",  # Cookie弹窗的第一个按钮
                "//button[contains(@class, 'primary')]",
            ]
            
            for selector in accept_selectors:
                try:
                    cookie_btn = driver.find_element(By.XPATH, selector)
                    if cookie_btn and cookie_btn.is_displayed():
                        print(f"   找到Cookie按钮，准备点击...")
                        # 滚动到底部（因为cookie弹窗在底部）
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        human_delay(1, 1.5)
                        
                        # 高亮显示按钮（调试用）
                        driver.execute_script("arguments[0].style.border='3px solid red'", cookie_btn)
                        human_delay(0.5, 1)
                        
                        # 强制点击
                        human_click(driver, cookie_btn)
                        print("✅ Cookie弹窗已关闭!")
                        cookie_closed = True
                        human_delay(2, 3)  # 等待弹窗消失
                        break
                except:
                    continue
            
            # 方法2: 尝试按ESC键关闭
            if not cookie_closed:
                print("   尝试按ESC键...")
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                human_delay(1, 2)
            
        except Exception as e:
            print(f"   Cookie处理异常: {e}")
        
        if cookie_closed:
            print("   Cookie弹窗处理完成")
        else:
            print("   ⚠️  未能自动关闭Cookie弹窗，继续尝试...")
        
        # 点击 Sign up with Builder ID
        print("正在点击 Sign up with Builder ID...")
        human_delay(4, 6)  # 增加等待时间，确保页面完全加载
        
        signup_clicked = False
        original_url = driver.current_url
        
        # 尝试查找包含关键文本的所有元素 (最多重试3次)
        for scan_attempt in range(3):
            if signup_clicked:
                break
                
            if scan_attempt > 0:
                print(f"   🔄 重试扫描 ({scan_attempt + 1}/3)...")
                human_delay(3, 5)
        
            try:
                print("   🔍 正在扫描页面元素...")
                # 查找任何包含 "Sign up with Builder ID" 或 "Builder-ID" 的可见元素
                # 注意：文本可能在子元素(如span)中，所以用 .// 来搜索后代文本
                key_texts = ["Sign up with Builder ID", "Mit Builder-ID anmelden", "Builder ID", "Builder-ID"]
                
                found_elements = []
                for text in key_texts:
                    # 先找精确包含文本的 span 元素
                    xpath = f"//span[contains(text(), '{text}')]"
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            found_elements.append(el)
                    
                    # 再找任意元素（包括后代文本）
                    if not found_elements:
                        xpath = f"//*[contains(., '{text}')]"
                        elements = driver.find_elements(By.XPATH, xpath)
                        for el in elements:
                            if el.is_displayed() and el.tag_name in ['a', 'button', 'span', 'div']:
                                found_elements.append(el)
                
                print(f"   找到 {len(found_elements)} 个相关元素")
                
                for i, element in enumerate(found_elements):
                    try:
                        # 获取元素的标签和文本
                        tag_name = element.tag_name
                        text_content = element.text
                        print(f"   元素 {i+1}: <{tag_name}> '{text_content[:20]}...'")
                        
                        # 如果元素本身是链接或按钮，直接点击
                        target_element = element
                        
                        # 如果不是，尝试向上查找父级链接或按钮 (最多查5层)
                        if tag_name not in ['a', 'button']:
                            parent = element
                            for _ in range(5):
                                try:
                                    parent = parent.find_element(By.XPATH, "./..")
                                    if parent.tag_name in ['a', 'button'] or parent.get_attribute('role') in ['button', 'link']:
                                        target_element = parent
                                        print(f"      找到父级可点击元素: <{parent.tag_name}>")
                                        break
                                except:
                                    break
                        
                        # 高亮并截图（调试）
                        driver.execute_script("arguments[0].style.border='3px solid red'; arguments[0].style.backgroundColor='yellow';", target_element)
                        
                        # 尝试点击
                        print(f"      👉 尝试点击...")
                        
                        # 优先使用 JS 点击 (最强力)
                        human_click(driver, target_element)
                        human_delay(2, 3)
                        
                        if driver.current_url != original_url:
                            print(f"✅ 成功跳转到: {driver.current_url}")
                            signup_clicked = True
                            break
                        
                        # 如果JS点击没反应，尝试 ActionChains
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(driver).move_to_element(target_element).click().perform()
                        human_delay(2, 3)
                        
                        if driver.current_url != original_url:
                            print(f"✅ 成功跳转到: {driver.current_url}")
                            signup_clicked = True
                            break
                            
                    except Exception as e:
                        print(f"      点击尝试失败: {e}")
                        continue
                    
                    if signup_clicked:
                        break
                        
            except Exception as e:
                print(f"   扫描元素时出错: {e}")

        # 如果上面的智能扫描失败，尝试最后的硬编码备选
        if not signup_clicked:
            print("⚠️  智能扫描未成功，尝试直接CSS定位...")
            try:
                # 尝试最常见的CSS类名组合 (根据AWS一般规律)
                css_selectors = [
                    "a[href*='signup']",
                    "a[href*='register']",
                    ".lb-btn-primary",
                    "button[type='submit']"
                ]
                for css in css_selectors:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, css)
                        for el in els:
                            if el.is_displayed() and "Builder ID" in el.text:
                                human_click(driver, el)
                                human_delay(2, 3)
                                if driver.current_url != original_url:
                                    signup_clicked = True
                                    break
                        if signup_clicked: break
                    except: continue
            except: pass

        if not signup_clicked:
            print("❌ 严重错误: 无法进入注册页面")
            driver.save_screenshot("debug_failed_click.png")
            # 这里不使用备用URL，因为用户反馈备用方案无效
            pass
        
        print(f"当前页面 URL: {driver.current_url}")
        
        # 截图
        driver.save_screenshot("screenshot.png")
        print("已截图当前页面")

        # 第三步：填写邮箱（带重试）
        print(f"正在填写邮箱: {email_address}")
        
        def safe_input(selector, value, max_retries=3):
            """安全输入函数，处理stale element"""
            for attempt in range(max_retries):
                try:
                    element = wait.until(EC.presence_of_element_located(selector))
                    element.click()
                    human_delay(0.3, 0.8)
                    element.clear()
                    human_type(element, value)
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"   输入重试 {attempt + 1}/{max_retries}...")
                        human_delay(1, 2)
                    else:
                        raise e
            return False
        
        safe_input((By.CSS_SELECTOR, 'input[placeholder="username@example.com"]'), email_address)
        driver.save_screenshot("screenshot.png")
        print("已填写邮箱")

        # 点击继续按钮
        human_delay(1, 2)
        print("正在点击继续...")
        continue_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="test-primary-button"]'))
        )
        continue_btn.click()

        # 等待姓名页面加载
        human_delay(3, 5)
        print(f"当前页面 URL: {driver.current_url}")
        driver.save_screenshot("screenshot.png")

        # 第四步：填写姓名（带重试）
        random_name = fake.name()
        print(f"正在填写姓名: {random_name}")
        
        # 增加一点随机行为
        driver.execute_script("window.scrollBy(0, 10)")
        human_delay(0.5, 1)
        
        # 更可靠的姓名输入方式
        name_input_success = False
        for name_attempt in range(3):
            try:
                # 等待输入框出现
                name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]')))
                
                # 点击输入框获取焦点
                name_input.click()
                human_delay(0.3, 0.5)
                
                # 使用 Ctrl+A 全选然后删除，比 clear() 更可靠
                from selenium.webdriver.common.keys import Keys
                name_input.send_keys(Keys.CONTROL + "a")
                human_delay(0.1, 0.2)
                name_input.send_keys(Keys.DELETE)
                human_delay(0.2, 0.4)
                
                # 输入姓名
                human_type(name_input, random_name)
                human_delay(0.5, 1)
                
                # 验证输入是否成功
                actual_value = name_input.get_attribute('value')
                if actual_value and len(actual_value) > 0:
                    print(f"   输入验证: '{actual_value}'")
                    name_input_success = True
                    break
                else:
                    print(f"   输入验证失败，重试...")
                    
            except Exception as e:
                print(f"   姓名输入重试 {name_attempt + 1}/3: {e}")
                human_delay(1, 2)
        
        if not name_input_success:
            print("⚠️ 姓名输入可能失败，继续尝试...")

        driver.save_screenshot("screenshot.png")
        print("已填写姓名")

        # 点击继续 (多语言兼容) - 带错误检测和多次重试
        max_continue_attempts = 5  # 增加到5次重试
        page_changed = False
        original_url = driver.current_url
        
        for continue_attempt in range(max_continue_attempts):
            human_delay(1, 2)
            print(f"正在点击继续... (尝试 {continue_attempt + 1}/{max_continue_attempts})")
            
            try:
                # 尝试多种方式找到继续按钮
                continue_btn = None
                continue_selectors = [
                    lang_selector.get_by_xpath('continue', 'button'),
                    (By.XPATH, "//button[contains(., 'Continue')]"),
                    (By.XPATH, "//button[contains(., '继续')]"),
                    (By.XPATH, "//button[@type='submit']"),
                    (By.CSS_SELECTOR, '[data-testid="test-primary-button"]'),
                ]
                
                for selector in continue_selectors:
                    try:
                        continue_btn = driver.find_element(*selector)
                        if continue_btn and continue_btn.is_displayed():
                            break
                    except:
                        continue
                
                if continue_btn:
                    # 滚动到按钮确保可见
                    driver.execute_script("arguments[0].scrollIntoView(true);", continue_btn)
                    human_delay(0.3, 0.5)
                    
                    # 尝试多种点击方式
                    try:
                        human_click(driver, continue_btn)
                    except:
                        driver.execute_script("arguments[0].click();", continue_btn)
                else:
                    print("   ⚠️ 未找到继续按钮")
                    continue
                    
            except Exception as e:
                print(f"   点击异常: {e}")
                continue
            
            # 等待页面响应 (稍微长一点)
            human_delay(3, 5)
            
            # 检查页面是否已跳转 (URL变化或标题变化)
            current_url = driver.current_url
            if current_url != original_url or 'verification' in current_url.lower() or 'code' in driver.title.lower():
                print(f"   ✅ 页面已跳转")
                page_changed = True
                break
            
            # 检测是否有错误弹窗/提示
            error_found = False
            try:
                # 更全面的错误检测
                error_selectors = [
                    "//*[contains(text(), 'error processing')]",
                    "//*[contains(text(), 'Error')]",
                    "//*[contains(text(), 'try again')]",
                    "//*[contains(text(), 'Sorry')]",
                    "//*[contains(@class, 'error')]",
                    "//*[contains(@class, 'alert')]",
                    "//div[contains(@role, 'alert')]",
                ]
                
                for error_xpath in error_selectors:
                    try:
                        error_elements = driver.find_elements(By.XPATH, error_xpath)
                        for el in error_elements:
                            if el.is_displayed():
                                error_text = el.text.strip()
                                if error_text and len(error_text) > 5:
                                    # 排除一些非错误的文本
                                    if 'required' not in error_text.lower():
                                        error_found = True
                                        print(f"   ⚠️ 检测到错误: {error_text[:60]}...")
                                        break
                        if error_found:
                            break
                    except:
                        continue
                
                if error_found:
                    # 尝试关闭错误弹窗
                    try:
                        close_selectors = [
                            "//button[contains(@aria-label, 'close')]",
                            "//button[contains(@class, 'close')]",
                            "//button[text()='×']",
                            "//button[text()='OK']",
                            "//button[text()='确定']",
                        ]
                        for close_xpath in close_selectors:
                            try:
                                close_btn = driver.find_element(By.XPATH, close_xpath)
                                if close_btn.is_displayed():
                                    close_btn.click()
                                    human_delay(1, 2)
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    # 按 ESC 尝试关闭
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        human_delay(1, 2)
                    except:
                        pass
                    
                    print(f"   🔄 等待后重试...")
                    human_delay(2, 4)  # 错误后等待更长时间
                    continue
                    
            except Exception as e:
                pass
            
            # 如果没有错误也没有跳转，可能需要再点一次
            if not error_found and not page_changed:
                print(f"   页面未变化，再次尝试...")
                human_delay(1, 2)
        
        if not page_changed:
            print("⚠️ 多次尝试后页面仍未跳转，继续执行...")
        
        driver.save_screenshot("screenshot.png")
        print(f"当前页面标题: {driver.title}")

        # 第五步：等待并获取验证码 (优先获取，因为可能页面还没加载完验证码就发过来了)
        print("正在等待验证码邮件...")
        human_delay(3, 5) # 给页面一点加载时间
        
        # 增加对 JSON 解析错误的保护
        try:
            # 此时页面应该在要求输入验证码
            if fixed_account:
                # 适配新的 IMAP OAuth 逻辑，传递完整的账号信息字典
                verification_code = get_verification_code_from_outlook(fixed_account)
            else:
                from services.email_service import wait_for_verification_email
                verification_code = wait_for_verification_email(jwt_token)
        except Exception as e:
            print(f"⚠️  获取验证码过程中出错: {e}")
            verification_code = None

        if verification_code:
            print(f"获取到验证码: {verification_code}")

            # 填写验证码
            try:
                print("正在寻找验证码输入框...")
                # 增加更长的等待，确保页面已稳定加载
                human_delay(4, 6)
                
                # 截图：验证码页面
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "step5_verification_page.png"))
                print(f"📸 截图已保存: step5_verification_page.png")
                
                # 等待输入框出现且可交互
                code_input = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder*="digit"], input[type="text"]'))
                )
                
                # 再等一下，防止点击时输入框跳动
                human_delay(1, 2)
                
                # 模拟更真实的人类行为：先移动鼠标到输入框
                actions = ActionChains(driver)
                actions.move_to_element(code_input).perform()
                human_delay(0.3, 0.6)
                
                code_input.click()
                human_delay(0.5, 1)
                
                # 逐个字符输入验证码，模拟人类打字
                for char in verification_code:
                    code_input.send_keys(char)
                    time.sleep(random.uniform(0.1, 0.25))  # 每个字符间隔
                
                print("已填写验证码")
                
                # 截图：填写验证码后
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "step5_after_code.png"))
                print(f"📸 截图已保存: step5_after_code.png")
                
                # 填写完后再等一下
                human_delay(1.5, 2.5)
                
                # 点击验证/继续
                # 用户反馈这里实际是“继续”按钮，不是 Verify
                verify_clicked = False
                verify_selectors = [
                   "//button[contains(., 'Verify')]", 
                   "//button[contains(., 'Continue')]",  # 增加 Continue
                   "//button[contains(., '继续')]",
                   "//button[@type='submit']"
                ]
                
                print("正在寻找 验证/继续 按钮...")
                for xpath in verify_selectors:
                    try:
                        verify_btn = driver.find_element(By.XPATH, xpath)
                        if verify_btn.is_displayed():
                            # 滚动到按钮并高亮
                            driver.execute_script("arguments[0].scrollIntoView(true);", verify_btn)
                            human_delay(0.5, 1)
                            driver.execute_script("arguments[0].click();", verify_btn)
                            verify_clicked = True
                            print(f"已点击按钮 (xpath: {xpath})")
                            break
                    except: continue
                
                if not verify_clicked:
                    print("⚠️  未找到明显的按钮，尝试按回车")
                    from selenium.webdriver.common.keys import Keys
                    code_input.send_keys(Keys.ENTER)
                
                # 点击后等待，检查是否有错误弹窗，如果有就再点一次 Continue
                print("等待页面响应...")
                human_delay(3, 5)
                
                # 截图：点击 Continue 后
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "step5_after_continue.png"))
                print(f"📸 截图已保存: step5_after_continue.png")
                
                # 检查是否有错误弹窗，如果有就再点一次 Continue (最多重试3次)
                for retry in range(3):
                    try:
                        page_source = driver.page_source
                        if "Error" in page_source or "error processing" in page_source or "Sorry" in page_source or "try again" in page_source.lower():
                            print(f"⚠️  检测到错误提示，再次点击 Continue... (重试 {retry + 1}/3)")
                            human_delay(1, 2)
                            for xpath in verify_selectors:
                                try:
                                    verify_btn = driver.find_element(By.XPATH, xpath)
                                    if verify_btn.is_displayed():
                                        # 模拟人类点击
                                        actions = ActionChains(driver)
                                        actions.move_to_element(verify_btn).perform()
                                        human_delay(0.2, 0.5)
                                        driver.execute_script("arguments[0].click();", verify_btn)
                                        print("✅ 已再次点击 Continue")
                                        human_delay(3, 5)
                                        break
                                except: continue
                        else:
                            break  # 没有错误，跳出重试循环
                    except: 
                        break
                
                # 点击后等待足够长的时间让页面跳转
                print("等待页面跳转 (由于代理可能较慢)...")
                human_delay(8, 12)

            except Exception as e:
                    print(f"⚠️  填写验证码失败: {e}")
        else:
            print("❌ 未能获取到验证码")

        # 第六步：设置密码
        print("正在准备设置密码...")
        human_delay(5, 8)  # 等待验证通过后的跳转
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "step6_before_password.png"))
        print(f"📸 截图已保存: {os.path.join(SCREENSHOT_DIR, 'step6_before_password.png')}")
        print(f"当前页面: {driver.current_url}")
        
        password = generate_strong_password()
        print(f"生成的密码: {password}")

        # 填写密码
        try:
            # 查找页面上所有的密码输入框
            password_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="password"]')
            
            if len(password_inputs) >= 1:
                print(f"找到 {len(password_inputs)} 个密码输入框")
                
                # 填写第一个密码框 (密码)
                human_delay(0.5, 1)
                password_inputs[0].click()
                human_type(password_inputs[0], password)
                print("已填写主密码")
                
                # 如果有第二个，填写第二个 (确认密码)
                if len(password_inputs) >= 2:
                    human_delay(0.5, 1)
                    password_inputs[1].click()
                    human_type(password_inputs[1], password)
                    print("已填写确认密码")
                # 如果没找到第二个但用户说有两个，尝试其他特征查找
                else: 
                     try:
                        confirm_selectors = [
                            'input[name="confirmPassword"]',
                            'input[placeholder="Confirm password"]', 
                            'input[placeholder="Re-enter password"]',
                            'input[id*="confirm"]'
                        ]
                        for sel in confirm_selectors:
                            try:
                                confirm_input = driver.find_element(By.CSS_SELECTOR, sel)
                                if confirm_input.is_displayed() and confirm_input != password_inputs[0]:
                                    human_delay(0.5, 1)
                                    confirm_input.click()
                                    human_type(confirm_input, password)
                                    print("已填写确认密码 (通过备用选择器)")
                                    break
                            except: continue
                     except: pass
                
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "step6_after_password.png"))
                print(f"📸 截图已保存: {os.path.join(SCREENSHOT_DIR, 'step6_after_password.png')}")
                
                # 点击创建/继续
                human_delay(1, 2)
                print("正在点击继续/创建账户...")
                
                # 查找提交按钮
                submit_selectors = [
                    "//button[contains(., 'Create AWS Builder ID')]",
                    "//button[contains(., 'Continue')]",
                    "//button[@type='submit']"
                ]
                
                for xpath in submit_selectors:
                    try:
                        btn = driver.find_element(By.XPATH, xpath)
                        if btn.is_displayed():
                            human_click(driver, btn)
                            break
                    except: continue
                    
            else:
                print("⚠️  未找到密码输入框，可能已经登录或流程不同")
        
        except Exception as e:
            print(f"⚠️  设置密码步骤异常: {e}")

        # 等待最终页面
        human_delay(5, 8)
        print(f"最终页面标题: {driver.title}")
        print(f"最终页面 URL: {driver.current_url}")
        driver.save_screenshot("final_success.png")

        # === Kiro OAuth 流程 ===
        kiro_token = None
        try:
            print("\n" + "=" * 60)
            print("🚀 开始 Kiro OAuth 获取 Token...")
            print("=" * 60)
            kiro_token = perform_kiro_oauth_in_browser(driver, email_address, password)
            if kiro_token:
                print("\n✅ Kiro Token 获取成功!")
                print(f"   access_token: {kiro_token.get('access_token', '')[:50]}...")
            else:
                print("\n⚠️  Kiro OAuth 未成功，账号已注册但无 Kiro Token")
        except Exception as e:
            print(f"\n⚠️  Kiro OAuth 异常: {e}")
            print("   账号已注册，可稍后手动获取 Kiro Token")

        # === AWS SSO OIDC 流程 (获取 aor 开头的 refresh_token) ===
        aws_sso_token = None
        try:
            print("\n" + "=" * 60)
            print("🔐 开始 AWS SSO OIDC 获取 Token (用于 Kiro Account Manager)...")
            print("=" * 60)
            
            # 使用已存在的邮件客户端
            mail_client = ChatGPTMailClient()
            
            aws_sso_token = perform_aws_sso_oidc_auto(
                driver=driver,
                email=email_address,
                password=password,
                mail_client=mail_client,
                region="us-east-1"
            )
            
            if aws_sso_token:
                print("\n✅ AWS SSO Token 获取成功!")
                print(f"   Refresh Token 前缀: {aws_sso_token.get('refresh_token', '')[:3]}")
                print(f"   Client ID: {aws_sso_token.get('client_id', '')[:20]}...")
            else:
                print("\n⚠️  AWS SSO OIDC 未成功")
        except Exception as e:
            print(f"\n⚠️  AWS SSO OIDC 异常: {e}")
            print("   账号已注册，可稍后手动获取 AWS SSO Token")

        # 保存账号信息 (无论如何都尝试保存，因为可能已经成功)
        save_account(email_address, password, random_name, jwt_token, kiro_token, aws_sso_token)
        print("\n✅ 账号流程结束，已保存信息到 accounts.jsonl")

    except Exception as e:
        print(f"过程发生错误: {e}")
        try:
            driver.save_screenshot("error_screenshot.png")
            # 即使出错也保存账号，便于后续检查
            if 'email_address' in locals() and 'password' in locals():
                save_account(email_address, password, random_name if 'random_name' in locals() else "Unknown", jwt_token if 'jwt_token' in locals() else "")
                print("⚠️  已保存部分账号信息")
        except: pass

    finally:
        # 使用浏览器工厂的清理函数
        cleanup_driver(driver)


def run_batch():
    """批量注册模式"""
    print("\n" + "=" * 60)
    print("🚀 AWS Builder ID 批量注册工具")
    print("=" * 60)
    
    # 询问注册数量
    while True:
        try:
            count_input = input("\n请输入要注册的账号数量 (直接回车默认1个): ").strip()
            if not count_input:
                count = 1
            else:
                count = int(count_input)
            
            if count <= 0:
                print("❌ 数量必须大于0")
                continue
            break
        except ValueError:
            print("❌ 请输入有效的数字")
    
    # 询问间隔时间
    if count > 1:
        while True:
            try:
                interval_input = input("请输入每个账号之间的间隔秒数 (直接回车默认30秒): ").strip()
                if not interval_input:
                    interval = 30
                else:
                    interval = int(interval_input)
                
                if interval < 0:
                    print("❌ 间隔不能为负数")
                    continue
                break
            except ValueError:
                print("❌ 请输入有效的数字")
    else:
        interval = 0
    
    print(f"\n📋 即将注册 {count} 个账号" + (f"，每个间隔 {interval} 秒" if count > 1 else ""))
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i in range(count):
        print(f"\n\n{'#' * 60}")
        print(f"# 正在注册第 {i + 1}/{count} 个账号")
        print(f"{'#' * 60}")
        
        try:
            run()
            success_count += 1
            print(f"\n✅ 第 {i + 1} 个账号注册流程完成")
        except Exception as e:
            fail_count += 1
            print(f"\n❌ 第 {i + 1} 个账号注册失败: {e}")
        
        # 如果不是最后一个，等待间隔
        if i < count - 1 and interval > 0:
            print(f"\n⏳ 等待 {interval} 秒后注册下一个...")
            time.sleep(interval)
    
    # 打印汇总
    print("\n\n" + "=" * 60)
    print("📊 批量注册完成汇总")
    print("=" * 60)
    print(f"   总计: {count} 个")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {fail_count} 个")
    print(f"   账号保存在: accounts.jsonl")
    print("=" * 60)


if __name__ == "__main__":
    run_batch()



