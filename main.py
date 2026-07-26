# --- dev_main.py (測試用的入口檔案) ---
import time
import data_fetchers as df
import utils
from config import INDICATORS

def fetch_all_indices():
    results = {}
    print("🚀 [Dev Test] 開始依序抓取數據...")
    
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
            
            results[key] = val
            if "Error" in str(val): time.sleep(1)
                
        except Exception as e:
            print(f"❌ {key} 發生例外: {e}")
            results[key] = "Error"
            
    return results

if __name__ == "__main__":
    # 1. 抓取
    results = fetch_all_indices()
    # 2. 大盤
    market_text = df.fetch_market_info()
    # 3. 總結
    summary = utils.calculate_summary(results)
    
    print("\n" + summary)
    
    # 4. 發送 Discord
    utils.send_wechat(results, market_text, summary)
    
    # 5. 存檔 CSV (關鍵測試點)
    print("正在寫入 CSV...")
    utils.save_csv(results)
