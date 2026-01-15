"""
多语言选择器模块
支持不同地区的本地化界面元素定位
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from selenium.webdriver.common.by import By
from config import REGION_CURRENT


class MultiLangSelector:
    """多语言选择器类"""
    
    def __init__(self):
        # 加载语言配置 (配置文件在项目根目录的 config/ 下)
        lang_config_path = Path(__file__).parent.parent.parent / "config" / "languages.yaml"
        with open(lang_config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        # 获取当前地区对应的语言
        self.current_lang = self._config['region_language_map'].get(
            REGION_CURRENT, 
            'en'  # 默认英语
        )
        
        # 获取所有语言的文本（用于兼容性）
        self.texts = self._config['languages']
        self.current_texts = self.texts.get(self.current_lang, self.texts['en'])
    
    def get_text(self, key):
        """获取当前语言的文本"""
        return self.current_texts.get(key, key)
    
    def get_all_text_variations(self, key):
        """获取所有语言版本的文本（用于创建兼容所有语言的选择器）"""
        variations = []
        for lang_code, lang_texts in self.texts.items():
            text = lang_texts.get(key)
            if text and text not in variations:
                variations.append(text)
        return variations
    
    def get_button_xpath(self, key):
        """
        生成多语言兼容的按钮 XPath
        例如: //button[contains(., 'Continue') or contains(., 'Weiter') or contains(., '続行')]
        """
        variations = self.get_all_text_variations(key)
        if not variations:
            return f"//button"
        
        # 构建 OR 条件
        conditions = [f"contains(., '{text}')" for text in variations]
        xpath = f"//button[{' or '.join(conditions)}]"
        return xpath
    
    def get_link_xpath(self, key):
        """
        生成多语言兼容的链接 XPath
        """
        variations = self.get_all_text_variations(key)
        if not variations:
            return f"//a"
        
        conditions = [f"contains(., '{text}')" for text in variations]
        xpath = f"//a[{' or '.join(conditions)}]"
        return xpath
    
    def get_text_xpath(self, key):
        """
        生成多语言兼容的任意元素 XPath（用于查找包含特定文本的元素）
        """
        variations = self.get_all_text_variations(key)
        if not variations:
            return f"//*"
        
        conditions = [f"contains(., '{text}')" for text in variations]
        xpath = f"//*[{' or '.join(conditions)}]"
        return xpath
    
    def get_by_xpath(self, key, element_type='button'):
        """
        获取 Selenium By 对象
        
        Args:
            key: 文本键名
            element_type: 'button', 'link', 'any'
        
        Returns:
            (By.XPATH, xpath_string)
        """
        if element_type == 'button':
            xpath = self.get_button_xpath(key)
        elif element_type == 'link':
            xpath = self.get_link_xpath(key)
        else:
            xpath = self.get_text_xpath(key)
        
        return (By.XPATH, xpath)
    
    def print_current_language(self):
        """打印当前使用的语言"""
        lang_names = {
            'de': '德语 (Deutsch)',
            'ja': '日语 (日本語)',
            'en': '英语 (English)'
        }
        lang_name = lang_names.get(self.current_lang, self.current_lang)
        print(f"🌍 界面语言: {lang_name}")
    
    def update_region(self, region_name):
        """动态更新地区"""
        self.current_lang = self._config['region_language_map'].get(
            region_name,
            'en'
        )
        self.current_texts = self.texts.get(self.current_lang, self.texts['en'])



# 创建全局实例
lang_selector = MultiLangSelector()


def get_continue_button_selector():
    """获取 Continue 按钮的多语言选择器"""
    return lang_selector.get_by_xpath('continue', 'button')


def get_signup_button_selector():
    """获取 Sign up 按钮的多语言选择器"""
    return lang_selector.get_by_xpath('sign_up_with_builder_id', 'any')
