# --- utils.py (v6.1: 完美防呆版 - 自动跳过休市日与周末) ---
import os
import requests
import datetime
import csv
import re
import pandas as pd  # 需要引入 pandas 来读取 CSV
import yfinance as yf  # 需要引入 yf 来确认真实日期
from config import INDICATORS, IMAGES
import data_fetchers as df


def extract_numeric_value(text):
    if not isinstance(text, str): return ""
    clean_text = text.replace('%', '').replace('+', '').replace(',', '')
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean_text)
    if match: return match.group()
    return ""


def get_indicator_status(key, value_in):
    value_str = value_in
    if key == 'AAII' and isinstance(value_in, tuple) and len(value_in) >= 3:
        value_str = value_in[2]

    if not value_str or "Error" in str(value_str) or "N/A" in str(value_str):
        return "⚠️ 无法判读"

    cfg = INDICATORS.get(key)
    if not cfg: return "⚪ 中性"

    try:
        clean_val = str(value_str).replace('%', '').replace('+', '').replace(',', '').split()[0]
        val = float(clean_val)
        thresholds = cfg['thresholds']

        if thresholds == 'ma_trend':
            if "(Above)" in str(value_str): return "🟢 多头排列" if key != 'HYG' else "🟢 资金流入"
            if "(Below)" in str(value_str): return "🔴 转弱/空头" if key != 'HYG' else "🔴 资金流出"
            return "⚪ 中性"

        if thresholds == 'arrow_trend':
            if "↗️" in str(value_str): return "🟢 Risk On"
            if "↘️" in str(value_str): return "🔴 Risk Off"
            return "⚪ 中性"

        g_limit, r_limit = thresholds

        if key == 'BTC':
            if val > g_limit: return "🟢 大涨 (Risk On)"
            if val < r_limit: return "🔴 大跌 (Risk Off)"
            return "⚪ 波动正常"

        if key == 'PUT_CALL':
            if val > g_limit: return "🟢 看空过度 (偏多)"
            if val < r_limit: return "🔴 看多过度 (偏空)"
            return "⚪ 中性"

        if key == 'VIX':
            if val > g_limit: return "🟢 市场恐慌 (偏多)"
            if val < r_limit: return "🔴 市场自满 (偏空)"
            return "⚪ 中性"

        if cfg.get('inverse'):
            if val <= g_limit: return "🟢 偏多"
            if val >= r_limit: return "🔴 偏空"
        else:
            if val >= g_limit: return "🟢 偏多"
            if val <= r_limit: return "🔴 偏空"

        return "⚪ 中性"
    except:
        return "⚪ 中性"


def calculate_summary(results):
    bulls = 0
    bears = 0
    for key, val in results.items():
        status = get_indicator_status(key, val)
        if "🟢" in status: bulls += 1
        if "🔴" in status: bears += 1

    concl = "⚪ 市场分歧，建议观望"
    if bulls > bears:
        concl = "🟢 市场偏向恐慌/机会 (Risk On)"
    elif bears > bulls:
        concl = "🔴 市场偏向贪婪/风险 (Risk Off)"
    return f"**🟢 多方**: {bulls} | **🔴 空方**: {bears}\n👉 {concl}"


def send_discord(results, market_text, summary):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url: return

    bulls = 0
    bears = 0
    for key, val in results.items():
        status = get_indicator_status(key, val)
        if "🟢" in status: bulls += 1
        if "🔴" in status: bears += 1

    embed_color = 0x95a5a6
    thumbnail_url = IMAGES['NEUTRAL']

    if bulls > bears:
        embed_color = 0x2ecc71
        thumbnail_url = IMAGES['BULL']
    elif bears > bulls:
        embed_color = 0xe74c3c
        thumbnail_url = IMAGES['BEAR']

    categories = {
        'macro': '🌊 宏观与资金 (Macro)',
        'struct': '🏗️ 结构与板块 (Struct)',
        'tech': '🌡️ 技术与情绪 (Tech)',
        'fund': '🐳 筹码与内资 (Fund)'
    }

    fields = []
    fields.append({"name": "🔮 市场情绪总结", "value": summary, "inline": False})
    fields.append({"name": "📊 美股大盘指数", "value": market_text, "inline": False})
    fields.append({"name": "\u200b", "value": "\u200b", "inline": False})

    cat_items = list(categories.items())
    for i, (cat_key, cat_name) in enumerate(cat_items):
        content = ""
        cat_indicators = {k: v for k, v in INDICATORS.items() if v['category'] == cat_key}
        for key, cfg in cat_indicators.items():
            val = results.get(key, "N/A")
            display_val = val
            if key == 'AAII' and isinstance(val, tuple) and len(val) >= 3:
                display_val = f"多{val[0]}% | 空{val[1]}%"
            status = get_indicator_status(key, val)
            content += f"> {cfg['name']}: **{display_val}** ({status})\n"

        fields.append({"name": cat_name, "value": content, "inline": False})
        if i < len(cat_items) - 1:
            fields.append({"name": "\u200b", "value": "\u200b", "inline": False})

    data = {
        "embeds": [{
            "title": f"📅 每日财经情绪日报 ({datetime.datetime.now().strftime('%Y-%m-%d')})",
            "color": embed_color,
            "fields": fields,
            "image": {"url": thumbnail_url},
            "footer": {"text": "财经 Discord 机器人"},
            "timestamp": datetime.datetime.now().isoformat()
        }]
    }
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"Discord Error: {e}")


def save_csv(results):
    try:
        folder = "data"
        if not os.path.exists(folder): os.makedirs(folder)
        file = "data/history.csv"

        # 1. 取得市场真实交易日期 (这是防呆的核心)
        try:
            # 抓取 SPX 历史资料来确认“最新的有效交易日”
            t = yf.Ticker("^GSPC")
            # 抓 5 天是为了避免长假 (如圣诞+周末)
            hist = t.history(period="5d")

            if not hist.empty:
                # 取得最后一笔资料的日期 (格式: YYYY-MM-DD)
                last_trade_date = hist.index[-1].strftime("%Y-%m-%d")
            else:
                # 万一 yfinance 挂了，只好退回到系统日期 (极少发生)
                print("⚠️ 无法取得市场日期，使用系统日期")
                last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"❌ 日期侦测失败: {e}")
            last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")

        print(f"📅 侦测到最新交易日为: {last_trade_date}")

        # 2. 检查 CSV 是否已存在该日期 (去重复)
        if os.path.exists(file):
            try:
                # 读取现有 CSV
                existing_df = pd.read_csv(file)
                # 检查 Date 栏位
                if 'Date' in existing_df.columns:
                    if last_trade_date in existing_df['Date'].values.astype(str):
                        print(f"🛑 日期 {last_trade_date} 已存在，今日不写入 (可能是周末或休市)。")
                        return  # <--- 关键！直接结束函数，不存档
            except Exception as e:
                print(f"⚠️ 读取 CSV 检查时发生错误 (可能档案损坏，将尝试附加): {e}")

        # 3. 准备数据 (AI 训练格式)
        fieldnames = [
            'Date',
            'SPX_Open', 'SPX_High', 'SPX_Low', 'SPX_Close', 'SPX_Volume',
            'NDX_Open', 'NDX_High', 'NDX_Low', 'NDX_Close', 'NDX_Volume',
            '10Y_Yield', '3M_Yield',
            'RSI', 'VIX', 'CNN', 'Put_Call',
            'DXY', 'BTC_Chg', 'HYG_Price',
            'Risk_Ratio', 'IWM_Price', 'SOXX_Price',
            'NAAIM', 'SKEW', 'AAII_Diff', 'Above_200MA'
        ]

        market_data = df.fetch_full_market_data()
        short_yield = df.fetch_short_term_yield()
        aaii_raw = results.get('AAII', "")
        aaii_val = f"{aaii_raw[2]:.1f}" if isinstance(aaii_raw, tuple) and len(
            aaii_raw) >= 3 else extract_numeric_value(str(aaii_raw))

        row = {
            'Date': last_trade_date,  # [使用真实交易日]

            'SPX_Open': market_data.get('SPX_Open', ''),
            'SPX_High': market_data.get('SPX_High', ''),
            'SPX_Low': market_data.get('SPX_Low', ''),
            'SPX_Close': market_data.get('SPX_Close', ''),
            'SPX_Volume': market_data.get('SPX_Volume', ''),

            'NDX_Open': market_data.get('NDX_Open', ''),
            'NDX_High': market_data.get('NDX_High', ''),
            'NDX_Low': market_data.get('NDX_Low', ''),
            'NDX_Close': market_data.get('NDX_Close', ''),
            'NDX_Volume': market_data.get('NDX_Volume', ''),

            '10Y_Yield': extract_numeric_value(str(results.get('BOND_10Y', ''))),
            '3M_Yield': extract_numeric_value(short_yield),

            'RSI': extract_numeric_value(str(results.get('RSI', ''))),
            'VIX': extract_numeric_value(str(results.get('VIX', ''))),
            'CNN': extract_numeric_value(str(results.get('CNN', ''))),
            'Put_Call': extract_numeric_value(str(results.get('PUT_CALL', ''))),
            'DXY': extract_numeric_value(str(results.get('DXY', ''))),
            'BTC_Chg': extract_numeric_value(str(results.get('BTC', ''))),
            'HYG_Price': extract_numeric_value(str(results.get('HYG', ''))),
            'Risk_Ratio': extract_numeric_value(str(results.get('RISK_RATIO', ''))),
            'IWM_Price': extract_numeric_value(str(results.get('IWM', ''))),
            'SOXX_Price': extract_numeric_value(str(results.get('SOXX', ''))),
            'NAAIM': extract_numeric_value(str(results.get('NAAIM', ''))),
            'SKEW': extract_numeric_value(str(results.get('SKEW', ''))),
            'AAII_Diff': aaii_val,
            'Above_200MA': extract_numeric_value(str(results.get('ABOVE_200_DAYS', '')))
        }

        with open(file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not os.path.exists(file) or os.stat(file).st_size == 0:
                writer.writeheader()
            writer.writerow(row)

        print(f"💾 数据已储存至: {file}")

    except Exception as e:
        print(f"CSV Error: {e}")