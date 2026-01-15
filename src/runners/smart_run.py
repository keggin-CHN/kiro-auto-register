#!/usr/bin/env python3
"""
智能启动脚本
自动根据代理IP的地理位置配置环境
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from managers.proxy_manager import proxy_manager
from helpers.multilang import lang_selector

def auto_configure_environment():
    """根据代理IP自动配置环境"""
    
    print("\n" + "=" * 60)
    print("🤖 智能环境配置")  
    print("=" * 60)
    
    # 获取代理
    proxy_url = None
    proxy_region = "usa"  # 默认地区
    
    if proxy_manager.use_proxy:
        print("\n🔄 获取代理中...")
        proxy_url = proxy_manager.get_proxy()
        
        if not proxy_url:
            print("⚠️  代理获取失败，使用默认美国环境")
        elif proxy_manager.proxy_location:
            # 使用代理IP的地理位置
            proxy_region = proxy_manager.proxy_location.get('region', 'usa')
            country = proxy_manager.proxy_location.get('country', 'Unknown')
            
            print(f"\n📍 检测到代理IP位置:")
            print(f"   国家: {country}")
            print(f"   自动配置环境: {proxy_region.upper()}")
    else:
        print("\n⚠️  代理未启用，使用默认美国环境")
    
    # 更新多语言选择器
    lang_selector.update_region(proxy_region)
    
    print("\n✅ 环境配置完成!")
    print(f"   地区: {proxy_region.upper()}")
    lang_selector.print_current_language()
    
    print("=" * 60)
    print("\n🚀 启动主程序...\n")
    
    # 保存配置到环境变量，供main.py使用
    import os
    os.environ['AUTO_REGION'] = proxy_region
    
    # 导入并运行主程序
    from runners.main import run
    run()


if __name__ == "__main__":
    try:
        auto_configure_environment()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
