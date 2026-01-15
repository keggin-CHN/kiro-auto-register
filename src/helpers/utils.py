import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import random
import requests
from config import REGION_CURRENT, REGION_PROFILES, DEVICE_TYPE

# 创建 HTTP 会话
http_session = requests.Session()


def get_region_config():
    """获取当前地区配置"""
    return REGION_PROFILES.get(REGION_CURRENT, REGION_PROFILES.get("usa"))


def get_user_agent():
    """获取当前地区和设备类型的随机 User-Agent"""
    region_config = get_region_config()
    
    # 根据设备类型选择对应的 UA 列表
    if DEVICE_TYPE == "mobile":
        user_agents = region_config.get("mobile_user_agents", [])
        # 如果没有移动 UA，回退到桌面 UA
        if not user_agents:
            user_agents = region_config.get("desktop_user_agents", [])
    else:
        user_agents = region_config.get("desktop_user_agents", [])
    
    # 兜底默认值
    if not user_agents:
        user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
            if DEVICE_TYPE == "mobile" else
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    return random.choice(user_agents)


def is_mobile():
    """判断当前是否为移动设备模式"""
    return DEVICE_TYPE == "mobile"


def get_locale():
    """获取当前地区的语言设置"""
    region_config = get_region_config()
    return region_config.get("locale", "en-US")


def get_timezone():
    """获取当前地区的时区"""
    region_config = get_region_config()
    return region_config.get("timezone", "America/New_York")


def get_accept_language():
    """获取当前地区的 Accept-Language"""
    region_config = get_region_config()
    return region_config.get("accept_language", "en-US,en;q=0.9")



def extract_verification_code(text: str):
    """
    从文本中提取验证码（6位数字）
    """
    if not text:
        return None
    
    # 匹配6位数字验证码
    patterns = [
        r'\b(\d{6})\b',  # 独立的6位数字
        r'code[:\s]+(\d{6})',  # code: 123456
        r'验证码[：:\s]+(\d{6})',  # 验证码：123456
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


# === 动态地区配置支持 ===

def get_region_config_by_name(region_name):
    """根据地区名称获取配置"""
    return REGION_PROFILES.get(region_name, REGION_PROFILES.get("usa"))


def get_user_agent_for_region(region_name):
    """获取指定地区的 User-Agent (强制 Windows + 动态版本号)"""
    
    # 动态生成 Chrome 版本号，避免使用固定列表被指纹识别
    # 主版本: 119 ~ 124
    major = random.randint(119, 124)
    # 次版本: 0.0.0
    build = random.randint(6000, 6999)
    patch = random.randint(100, 200)
    
    version = f"{major}.0.{build}.{patch}"
    
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"


def get_locale_for_region(region_name):
    """获取指定地区的语言设置"""
    region_config = get_region_config_by_name(region_name)
    return region_config.get("locale", "en-US")


def get_timezone_for_region(region_name):
    """获取指定地区的时区"""
    region_config = get_region_config_by_name(region_name)
    return region_config.get("timezone", "America/New_York")


def get_accept_language_for_region(region_name):
    """获取指定地区的 Accept-Language"""
    region_config = get_region_config_by_name(region_name)
    return region_config.get("accept_language", "en-US,en;q=0.9")
