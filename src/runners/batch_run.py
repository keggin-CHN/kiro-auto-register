import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import random
from multiprocessing import Pool, freeze_support
from runners.main import run
from services.outlook_accounts import OUTLOOK_ACCOUNTS

def run_wrapper(i):
    """包装函数，用于在进程中运行"""
    # 确保索引不越界
    if i >= len(OUTLOOK_ACCOUNTS):
        print(f"❌ 进程 {i+1} 跳过: 没有更多可用的账号")
        return

    account = OUTLOOK_ACCOUNTS[i]
    print(f"🚀 进程 {i+1} 准备启动 (账号: {account['email']})...")
    
    try:
        # 增加延迟到 20 秒，确保 undetected_chromedriver 完成驱动文件打补丁，防止 WinError 183 文件锁冲突
        delay = i * 20
        if delay > 0:
            print(f"⏳ 进程 {i+1} 将在 {delay} 秒后启动...")
            time.sleep(delay)
            
        print(f"🎬 进程 {i+1} 正式开始运行")
        # 传递固定账号
        run(fixed_account=account)
        
    except Exception as e:
        print(f"❌ 进程 {i+1} 异常: {e}")
    finally:
        print(f"🏁 进程 {i+1} 结束")

def batch_run(count=None):
    """
    并发执行批量任务
    :param count: 并发数量 (默认使用账号列表长度)
    """
    if count is None:
        count = len(OUTLOOK_ACCOUNTS)
        
    print(f"🚀 开始多进程批量注册，并发数量: {count}")
    print(f"📋 使用 Outlook 账号列表 ({len(OUTLOOK_ACCOUNTS)} 个)")
    print("⚠️ 注意：这将同时打开多个浏览器窗口，请确保内存充足")
    print("⚠️ 结果将保存到 accounts.jsonl (每行一条)")
    
    # 稍微等待一下让用户看清提示
    time.sleep(2)

    # 这里的 processes=count 就是并发数
    with Pool(processes=count) as pool:
        # 创建任务列表
        # 使用 count 数量，最大不超过账号总数
        actual_count = min(count, len(OUTLOOK_ACCOUNTS))
        pool.map(run_wrapper, range(actual_count))
        
    print("\n🎉 所有并发任务已完成！")

if __name__ == "__main__":
    freeze_support() # Windows 必须
    # 默认跑完所有账号
    batch_run()
