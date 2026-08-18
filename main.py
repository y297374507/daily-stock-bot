# --- main.py ---
import time
import data_fetchers as df
import utils
from config import INDICATORS


def fetch_all_indices():
    results = {}
    print("🚀 开始依序抓取数据...")
    for key, cfg in INDICATORS.items():
        print(f"[{key}] 正在抓取 ({cfg['name']})...")
        try:
            if cfg['type'] == 'price':
                val = df.fetch_yf_price(cfg['ticker'], cfg.get('correction', 1.0))
            elif cfg['type'] == 'trend':
                val = df.fetch_yf_trend(cfg['ticker'])
            elif cfg['type'] == 'custom':
                val = cfg['func']()
            elif cfg['type'] == 'external':
                val = cfg['func']()
            else:
                val = "N/A"
            results[key] = val
        except Exception as e:
            print(f"❌ {key} 发生异常: {e}")
            results[key] = "N/A"
    return results


if __name__ == "__main__":
    start_time = time.time()

    # 1. 抓取所有指标
    results = fetch_all_indices()

    # 2. 大盘文本
    market_text = df.fetch_market_info()

    # 3. 情绪总结
    summary = utils.calculate_summary(results)

    print("\n" + "=" * 30)
    print(summary)
    print("=" * 30 + "\n")

    # 4. 发送 Discord
    print("📢 正在发送 Discord 通知...")
    utils.send_discord(results, market_text, summary)

    # 5. 写入 CSV
    print("💾 正在写入 CSV 历史数据...")
    utils.save_csv(results)

    # 6. 用 CSV 最新数据生成干净的 index.html
    print("🌐 正在根据 CSV 生成 index.html...")
    utils.generate_html_from_csv()

    elapsed_time = time.time() - start_time
    print(f"✨ 全部任务完成！总耗时: {elapsed_time:.2f} 秒")
