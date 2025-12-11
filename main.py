# main.py
import time
import signal
import sys
from config.settings import Settings
from services.trader_manager import TraderManager
from utils.logger import logger

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
        trader_id_str = str(trader_id) if trader_id else "N/A"
        print(f"  - {status['name']} ({trader_id_str[:8]}...) | 扫描间隔: {status['scan_interval_minutes']}分钟")
    
    if not all_traders:
        print("⚠️ 没有可用的交易员")
        return
    
    # 3. 启动所有交易员（参考NOFX：启动所有已加载的交易员）
    print(f"\n{'=' * 60}")
    print(f"🚀 启动所有交易员...")
    print(f"{'=' * 60}")
    
    started_count = trader_manager.start_all_traders()
    print(f"✅ 成功启动 {started_count} 个交易员")
    
    # 4. 设置信号处理，优雅退出（参考NOFX的优雅关闭机制）
    def signal_handler(sig, frame):
        print(f"\n\n{'=' * 60}")
        print("🛑 收到停止信号，正在停止所有交易员...")
        print(f"{'=' * 60}")
        stopped_count = trader_manager.stop_all_traders()
        print(f"✅ 已停止 {stopped_count} 个交易员")
        print("👋 程序退出")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill命令
    
    # 5. 主循环：保持程序运行（参考NOFX：主程序持续运行直到收到停止信号）
    print(f"\n{'=' * 60}")
    print("✅ 所有交易员已启动，程序将持续运行...")
    print("💡 按 Ctrl+C 停止所有交易员并退出")
    print(f"{'=' * 60}\n")
    
    # 定期输出状态（与K线时间匹配，默认3分钟）
    last_status_time = time.time()
    # 获取所有交易员的最小扫描间隔，或默认3分钟
    min_scan_interval = 180  # 默认3分钟
    if all_traders:
        min_scan_interval = min(
            trader.get_status().get('scan_interval_minutes', 3) * 60
            for trader in all_traders.values()
        )
    status_interval = min_scan_interval
    
    try:
        # 无限循环，保持主线程运行
        # 每个trader在自己的线程中运行扫描循环（scan_interval_minutes间隔）
        while True:
            time.sleep(1)
            
            # 定期输出交易员状态
            current_time = time.time()
            if current_time - last_status_time >= status_interval:
                print(f"\n📊 交易员状态检查 ({time.strftime('%Y-%m-%d %H:%M:%S')}):")
                for trader_id, trader in trader_manager.get_all_traders().items():
                    status = trader.get_status()
                    trader_id_str = str(trader_id) if trader_id else "N/A"
                    running_status = "✅ 运行中" if status.get('is_running') else "❌ 已停止"
                    print(f"  - {status['name']} ({trader_id_str[:8]}...): {running_status}")
                last_status_time = current_time
                
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()