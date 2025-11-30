# main.py
import time
from config.settings import Settings
from services.trader_manager import TraderManager

def main():
    settings = Settings()
    trader_manager = TraderManager(settings)
    
    print("=" * 60)
    print("🚀 开始加载交易员...")
    print("=" * 60)
    
    # 1. 从数据库加载所有交易员
    success_count = trader_manager.load_traders_from_database()
    print(f"\n✅ 成功加载 {success_count} 个交易员")
    
    # 2. 获取所有已加载的交易员
    all_traders = trader_manager.get_all_traders()
    print(f"\n📋 已加载的交易员列表:")
    for trader_id, trader in all_traders.items():
        status = trader.get_status()
        # 修复：将 UUID 转换为字符串
        trader_id_str = str(trader_id) if trader_id else "N/A"
        print(f"  - {status['name']} ({trader_id_str[:8]}...) | 扫描间隔: {status['scan_interval_minutes']}分钟")
    
    if not all_traders:
        print("⚠️ 没有可用的交易员")
        return
    
    # 3. 启动第一个交易员进行测试
    first_trader_id = list(all_traders.keys())[0]
    first_trader = all_traders[first_trader_id]
    trader_name = first_trader.get_status()['name']
    
    print(f"\n{'=' * 60}")
    print(f"🧪 测试启动交易员: {trader_name}")
    print(f"{'=' * 60}")
    
    # 启动交易员
    if trader_manager.start_trader(str(first_trader_id)):  # 确保传递字符串
        print(f"✅ 交易员 {trader_name} 已启动")
        
        # 等待几秒，观察扫描是否工作
        print(f"\n⏳ 等待 10 秒，观察扫描循环...")
        for i in range(10):
            time.sleep(1)
            status = trader_manager.get_trader_status(str(first_trader_id))  # 确保传递字符串
            if status:
                print(f"  [{i+1}s] 状态: {'运行中' if status.get('is_running') else '已停止'}")
        
        # 检查状态
        status = trader_manager.get_trader_status(str(first_trader_id))  # 确保传递字符串
        print(f"\n📊 交易员状态:")
        print(f"  - ID: {status.get('id', 'N/A')}")
        print(f"  - 名称: {status.get('name', 'N/A')}")
        print(f"  - 运行状态: {'✅ 运行中' if status.get('is_running') else '❌ 已停止'}")
        
        # 停止交易员
        print(f"\n{'=' * 60}")
        print(f"🛑 停止交易员: {trader_name}")
        print(f"{'=' * 60}")
        
        if trader_manager.stop_trader(str(first_trader_id)):  # 确保传递字符串
            print(f"✅ 交易员 {trader_name} 已停止")
        
        # 再次检查状态
        status = trader_manager.get_trader_status(str(first_trader_id))  # 确保传递字符串
        print(f"\n📊 最终状态: {'✅ 运行中' if status and status.get('is_running') else '❌ 已停止'}")
    else:
        print(f"❌ 启动交易员 {trader_name} 失败")
    
    print(f"\n{'=' * 60}")
    print("✅ 验证完成")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()