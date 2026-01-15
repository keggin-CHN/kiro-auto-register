#!/usr/bin/env python3
"""
单个 Outlook 账号注册脚本
使用第一个可用的 Outlook 账号进行注册
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from services.outlook_accounts import OUTLOOK_ACCOUNTS
from managers.proxy_manager import proxy_manager
from helpers.multilang import lang_selector


def single_outlook_run(account_index=0):
    """
    使用指定索引的 Outlook 账号进行单次注册
    :param account_index: 账号索引 (0-4)
    """
    
    if account_index >= len(OUTLOOK_ACCOUNTS):
        print(f"❌ 账号索引 {account_index} 超出范围，共有 {len(OUTLOOK_ACCOUNTS)} 个账号")
        return
    
    account = OUTLOOK_ACCOUNTS[account_index]
    
    print("\n" + "=" * 60)
    print("📧 单账号 Outlook 注册模式")
    print("=" * 60)
    print(f"使用账号: {account['email']}")
    print(f"账号索引: {account_index + 1}/{len(OUTLOOK_ACCOUNTS)}")
    
    # 智能配置环境 (根据代理IP)
    proxy_region = "usa"
    
    if proxy_manager.use_proxy:
        print("\n🔄 获取代理中...")
        proxy_url = proxy_manager.get_proxy()
        
        if proxy_url and proxy_manager.proxy_location:
            proxy_region = proxy_manager.proxy_location.get('region', 'usa')
            country = proxy_manager.proxy_location.get('country', 'Unknown')
            print(f"📍 代理IP位置: {country} -> 环境: {proxy_region.upper()}")
    
    # 更新语言选择器
    lang_selector.update_region(proxy_region)
    os.environ['AUTO_REGION'] = proxy_region
    
    print(f"\n🌍 地区环境: {proxy_region.upper()}")
    lang_selector.print_current_language()
    print("=" * 60)
    print("\n🚀 开始注册...\n")
    
    # 运行主程序
    from runners.main import run
    run(fixed_account=account)


if __name__ == "__main__":
    # 默认使用第一个账号，可以通过命令行参数指定
    # python single_outlook_run.py 0  # 使用第1个账号
    # python single_outlook_run.py 2  # 使用第3个账号
    
    account_idx = 0
    if len(sys.argv) > 1:
        try:
            account_idx = int(sys.argv[1])
        except ValueError:
            print("⚠️ 参数无效，使用默认账号索引 0")
    
    try:
        single_outlook_run(account_idx)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
