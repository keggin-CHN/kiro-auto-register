"""
IP地理位置查询模块
根据代理IP自动识别地区并设置环境
"""

import requests


def get_ip_location(ip_address):
    """
    查询IP地址的地理位置
    
    Args:
        ip_address: IP地址字符串
    
    Returns:
        dict: 包含国家代码、国家名、时区等信息
              例如: {'country_code': 'US', 'country': 'United States', 'timezone': 'America/New_York'}
              失败返回None
    """
    # 尝试多个免费IP查询服务
    services = [
        {
            'name': 'ip-api.com',
            'url': f'http://ip-api.com/json/{ip_address}',
            'parser': parse_ipapi
        },
        {
            'name': 'ipapi.co',
            'url': f'https://ipapi.co/{ip_address}/json/',
            'parser': parse_ipapico
        },
        {
            'name': 'ipwhois.app',
            'url': f'http://ipwhois.app/json/{ip_address}',
            'parser': parse_ipwhois
        }
    ]
    
    for service in services:
        try:
            print(f"🔍 正在查询IP地理位置 ({service['name']})...")
            response = requests.get(service['url'], timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                result = service['parser'](data)
                
                if result and result.get('country_code'):
                    print(f"✅ IP地理位置: {result.get('country')} ({result.get('country_code')})")
                    return result
        except Exception as e:
            print(f"   跳过 {service['name']}: {e}")
            continue
    
    print("⚠️  无法查询IP地理位置，将使用默认设置")
    return None


def parse_ipapi(data):
    """解析 ip-api.com 的返回数据"""
    if data.get('status') != 'success':
        return None
    
    return {
        'country_code': data.get('countryCode', ''),
        'country': data.get('country', ''),
        'timezone': data.get('timezone', ''),
        'city': data.get('city', ''),
        'region': data.get('regionName', ''),
        'isp': data.get('isp', '')
    }


def parse_ipapico(data):
    """解析 ipapi.co 的返回数据"""
    return {
        'country_code': data.get('country_code', ''),
        'country': data.get('country_name', ''),
        'timezone': data.get('timezone', ''),
        'city': data.get('city', ''),
        'region': data.get('region', ''),
        'isp': data.get('org', '')
    }


def parse_ipwhois(data):
    """解析 ipwhois.app 的返回数据"""
    if not data.get('success'):
        return None
    
    return {
        'country_code': data.get('country_code', ''),
        'country': data.get('country', ''),
        'timezone': data.get('timezone', ''),
        'city': data.get('city', ''),
        'region': data.get('region', ''),
        'isp': data.get('isp', '')
    }


def map_country_to_region(country_code):
    """
    将国家代码映射到我们配置的地区
    
    Args:
        country_code: 两字母国家代码（如 US, DE, JP）
    
    Returns:
        str: 地区名称 ('usa', 'germany', 'japan' 等)，未知返回 'usa'
    """
    # 国家代码到地区的映射
    mapping = {
        # 德国和德语区
        'DE': 'germany',
        'AT': 'germany',  # 奥地利，也用德语
        'CH': 'germany',  # 瑞士（部分德语区）
        
        # 日本
        'JP': 'japan',
        
        # 美国和英语区
        'US': 'usa',
        'CA': 'usa',  # 加拿大
        'GB': 'usa',  # 英国
        'AU': 'usa',  # 澳大利亚
        'NZ': 'usa',  # 新西兰
        'IE': 'usa',  # 爱尔兰
    }
    
    region = mapping.get(country_code.upper(), 'usa')
    return region


def get_region_config_from_ip(ip_address):
    """
    根据IP地址获取推荐的地区配置
    
    Args:
        ip_address: IP地址
    
    Returns:
        dict: {
            'region': 地区名称,
            'country_code': 国家代码,
            'country': 国家名称,
            'timezone': 时区,
            ...
        }
    """
    location = get_ip_location(ip_address)
    
    if not location:
        return {
            'region': 'usa',
            'country_code': 'US',
            'country': 'United States',
            'timezone': 'America/New_York'
        }
    
    country_code = location.get('country_code', 'US')
    region = map_country_to_region(country_code)
    
    return {
        'region': region,
        'country_code': country_code,
        'country': location.get('country', ''),
        'timezone': location.get('timezone', ''),
        'city': location.get('city', ''),
        'isp': location.get('isp', '')
    }


def extract_ip_from_proxy_url(proxy_url):
    """
    从代理URL中提取IP地址
    
    Args:
        proxy_url: 代理URL，如 http://1.2.3.4:8080 或 http://user:pass@1.2.3.4:8080
    
    Returns:
        str: IP地址，失败返回None
    """
    try:
        # 移除协议前缀
        url = proxy_url
        if '://' in url:
            url = url.split('://')[1]
        
        # 移除认证信息
        if '@' in url:
            url = url.split('@')[1]
        
        # 提取IP（去掉端口）
        ip = url.split(':')[0]
        
        return ip
    except:
        return None
