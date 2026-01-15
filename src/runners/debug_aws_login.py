"""
调试 AWS 登录页面元素
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.browser_factory import create_driver as factory_create_driver, cleanup_driver
from services.kiro_oauth import KiroOAuthClient
from selenium.webdriver.common.by import By
import time

def debug_aws_login():
    """调试 AWS 登录页面"""
    
    print("🌐 启动浏览器...")
    driver = factory_create_driver()
    
    try:
        # 获取 OAuth URL
        client = KiroOAuthClient()
        init_result = client.initiate_login("BuilderId")
        authorize_url = init_result["authorize_url"]
        
        print(f"📌 打开授权 URL...")
        driver.get(authorize_url)
        time.sleep(5)
        
        print(f"当前 URL: {driver.current_url}")
        
        # 查找所有 input 元素
        print("\n🔍 查找所有 input 元素:")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for i, inp in enumerate(inputs):
            try:
                print(f"  [{i}] type={inp.get_attribute('type')}, name={inp.get_attribute('name')}, "
                      f"id={inp.get_attribute('id')}, placeholder={inp.get_attribute('placeholder')}, "
                      f"displayed={inp.is_displayed()}")
            except:
                pass
        
        # 查找所有 button 元素
        print("\n🔍 查找所有 button 元素:")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for i, btn in enumerate(buttons):
            try:
                print(f"  [{i}] type={btn.get_attribute('type')}, text={btn.text[:50]}, displayed={btn.is_displayed()}")
            except:
                pass
        
        # 打印页面源码前1000字符
        print("\n📄 页面部分源码:")
        page_source = driver.page_source
        # 找 input 相关的部分
        import re
        input_matches = re.findall(r'<input[^>]*>', page_source)
        for m in input_matches[:10]:
            print(f"  {m[:200]}")
            
        input("\n按 Enter 关闭浏览器...")
        
    finally:
        cleanup_driver(driver)


if __name__ == "__main__":
    debug_aws_login()
