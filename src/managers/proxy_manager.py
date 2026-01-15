"""
代理管理模块
支持静态代理和动态API代理
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from config import (
    REGION_USE_PROXY,
    REGION_PROXY_MODE,
    REGION_PROXY_URL,
    REGION_PROXY_API,
    HTTP_TIMEOUT
)


class ProxyManager:
    """代理管理器"""
    
    def __init__(self):
        self.use_proxy = REGION_USE_PROXY
        self.proxy_mode = REGION_PROXY_MODE
        self.static_proxy = REGION_PROXY_URL
        self.api_config = REGION_PROXY_API
        self.current_proxy = None
        self.proxy_location = None  # 存储代理IP的地理位置信息
    
    def get_proxy(self):
        """
        获取代理
        
        Returns:
            str: 代理URL (例如: http://ip:port 或 socks5://ip:port)
            None: 如果不使用代理或获取失败
        """
        if not self.use_proxy:
            return None
        
        if self.proxy_mode == "static":
            # 使用静态代理
            self.current_proxy = self.static_proxy
            return self.static_proxy
        
        elif self.proxy_mode == "dynamic":
            # 从API获取动态代理
            return self._fetch_proxy_from_api()
        
        return None
    
    def _fetch_proxy_from_api(self):
        """从API获取代理IP"""
        if not self.api_config or not self.api_config.get('url'):
            print("⚠️  代理API未配置")
            return None
        
        api_url = self.api_config['url']
        timeout = self.api_config.get('timeout', 10)
        protocol = self.api_config.get('protocol', 'http')
        auth_required = self.api_config.get('auth_required', False)
        
        try:
            print(f"🔄 正在从API获取代理...")
            response = requests.get(api_url, timeout=timeout)
            
            if response.status_code == 200:
                # 获取返回的 IP:PORT
                proxy_text = response.text.strip()
                
                # 清理可能的换行符和空格
                proxy_text = proxy_text.replace('\n', '').replace('\r', '').strip()
                
                if not proxy_text:
                    print("⚠️  API返回空内容")
                    return None
                
                # 构建完整的代理URL
                if auth_required:
                    username = self.api_config.get('username', '')
                    password = self.api_config.get('password', '')
                    proxy_url = f"{protocol}://{username}:{password}@{proxy_text}"
                else:
                    proxy_url = f"{protocol}://{proxy_text}"
                
                self.current_proxy = proxy_url
                print(f"✅ 代理获取成功: {proxy_text}")
                
                # 查询代理IP的地理位置
                self._query_proxy_location(proxy_text.split(':')[0])
                
                return proxy_url
            else:
                print(f"⚠️  API请求失败: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⚠️  API请求超时 (>{timeout}秒)")
            return None
        except Exception as e:
            print(f"⚠️  获取代理失败: {e}")
            return None
    
    def _query_proxy_location(self, ip_address):
        """查询代理IP的地理位置"""
        try:
            from helpers.ip_location import get_region_config_from_ip
            self.proxy_location = get_region_config_from_ip(ip_address)
        except Exception as e:
            print(f"   查询IP位置失败: {e}")
            self.proxy_location = None
    
    def test_proxy(self, proxy_url=None):
        """
        测试代理是否可用
        
        Args:
            proxy_url: 要测试的代理URL，如果为None则测试当前代理
        
        Returns:
            bool: True表示可用，False表示不可用
        """
        if proxy_url is None:
            proxy_url = self.current_proxy
        
        if not proxy_url:
            return False
        
        try:
            print(f"🔍 正在测试代理...")
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试访问一个轻量级的网站
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                ip_info = response.json()
                print(f"✅ 代理测试成功！当前IP: {ip_info.get('origin', 'Unknown')}")
                return True
            else:
                print(f"⚠️  代理测试失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  代理测试失败: {e}")
            return False
    
    def get_current_proxy(self):
        """获取当前使用的代理"""
        return self.current_proxy
    
    def print_proxy_info(self):
        """打印代理信息"""
        if not self.use_proxy:
            print("🔒 代理: 未启用")
            return
        
        print(f"🔒 代理模式: {self.proxy_mode.upper()}")
        
        if self.proxy_mode == "static" and self.static_proxy:
            print(f"   静态代理: {self.static_proxy}")
        elif self.proxy_mode == "dynamic":
            if self.current_proxy:
                # 隐藏完整代理信息，只显示IP部分
                display_proxy = self.current_proxy.split('@')[-1] if '@' in self.current_proxy else self.current_proxy
                print(f"   动态代理: {display_proxy}")
            else:
                print(f"   动态代理: 等待获取...")


# 创建全局代理管理器实例
proxy_manager = ProxyManager()


def get_proxy():
    """获取代理的便捷函数"""
    return proxy_manager.get_proxy()


def test_current_proxy():
    """测试当前代理的便捷函数"""
    return proxy_manager.test_proxy()
