# --- utils.py (v6.6: 增加涨跌幅对比 + 比特币图标优化) ---
import os
import requests
import datetime
import csv
import re
import pandas as pd
import yfinance as yf
from config import INDICATORS, IMAGES
import data_fetchers as df


def extract_numeric_value(text):
    if not isinstance(text, str):
        return ""
    clean_text = text.replace('%', '').replace('+', '').replace(',', '')
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean_text)
    if match:
        return match.group()
    return ""


def get_indicator_status(key, value_in):
    value_str = value_in
    if key == 'AAII' and isinstance(value_in, tuple) and len(value_in) >= 3:
        value_str = value_in[2]
    if not value_str or "Error" in str(value_str) or "N/A" in str(value_str) or str(value_str).lower() == "nan":
        return "⚠️ 无法判读"
    cfg = INDICATORS.get(key)
    if not cfg:
        return "⚪ 中性"
    try:
        clean_val = str(value_str).replace('%', '').replace('+', '').replace(',', '').split()[0]
        val = float(clean_val)
        thresholds = cfg['thresholds']
        if thresholds == 'ma_trend':
            if "(Above)" in str(value_str):
                return "🟢 多头排列" if key != 'HYG' else "🟢 资金流入"
            if "(Below)" in str(value_str):
                return "🔴 转弱/空头" if key != 'HYG' else "🔴 资金流出"
            return "⚪ 中性"
        if thresholds == 'arrow_trend':
            if "↗️" in str(value_str):
                return "🟢 Risk On"
            if "↘️" in str(value_str):
                return "🔴 Risk Off"
            return "⚪ 中性"
        g_limit, r_limit = thresholds
        if key == 'BTC':
            if val > g_limit:
                return "🟢 大涨 (Risk On)"
            if val < r_limit:
                return "🔴 大跌 (Risk Off)"
            return "⚪ 波动正常"
        if key == 'PUT_CALL':
            if val > g_limit:
                return "🟢 看空过度 (偏多)"
            if val < r_limit:
                return "🔴 看多过度 (偏空)"
            return "⚪ 中性"
        if key == 'VIX':
            if val > g_limit:
                return "🟢 市场恐慌 (偏多)"
            if val < r_limit:
                return "🔴 市场自满 (偏空)"
            return "⚪ 中性"
        if cfg.get('inverse'):
            if val <= g_limit:
                return "🟢 偏多"
            if val >= r_limit:
                return "🔴 偏空"
        else:
            if val >= g_limit:
                return "🟢 偏多"
            if val <= r_limit:
                return "🔴 偏空"
        return "⚪ 中性"
    except:
        return "⚪ 中性"


def calculate_summary(results):
    bulls = 0
    bears = 0
    for key, val in results.items():
        status = get_indicator_status(key, val)
        if "🟢" in status:
            bulls += 1
        if "🔴" in status:
            bears += 1
    concl = "⚪ 市场分歧，建议观望"
    if bulls > bears:
        concl = "🟢 市场偏向恐慌/机会 (Risk On)"
    elif bears > bulls:
        concl = "🔴 市场偏向贪婪/风险 (Risk Off)"
    return f"**🟢 多方**: {bulls} | **🔴 空方**: {bears}\n👉 {concl}"


def send_discord(results, market_text, summary):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    bulls = 0
    bears = 0
    for key, val in results.items():
        status = get_indicator_status(key, val)
        if "🟢" in status:
            bulls += 1
        if "🔴" in status:
            bears += 1
    embed_color = 0x95a5a6
    thumbnail_url = IMAGES.get('NEUTRAL', '')
    if bulls > bears:
        embed_color = 0x2ecc71
        thumbnail_url = IMAGES.get('BULL', '')
    elif bears > bulls:
        embed_color = 0xe74c3c
        thumbnail_url = IMAGES.get('BEAR', '')
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


def _safe(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "n/a", "null"):
        return "—"
    return s


def _calc_change(curr, prev):
    """计算涨跌幅，返回 (显示文字, css class)"""
    try:
        c = float(curr)
        p = float(prev)
        if p == 0:
            return "—", "neutral"
        chg = (c - p) / p * 100
        if chg > 0:
            return f"+{chg:.2f}%", "bull"
        elif chg < 0:
            return f"{chg:.2f}%", "bear"
        else:
            return "0.00%", "neutral"
    except:
        return "—", "neutral"


def _get_status(col, val):
    """返回 (显示文字, css class)"""
    if val == "—":
        return "—", "neutral"
    try:
        v = float(val)
    except:
        return "中性", "neutral"

    if col == "VIX":
        if v >= 25: return "偏多 (恐慌)", "bull"
        if v <= 15: return "偏空 (自满)", "bear"
        return "中性", "neutral"
    elif col == "CNN":
        if v <= 25: return "偏多 (恐惧)", "bull"
        if v >= 75: return "偏空 (贪婪)", "bear"
        if v >= 55: return "偏空 (过热)", "bear"
        return "中性", "neutral"
    elif col == "RSI":
        if v <= 30: return "偏多 (超卖)", "bull"
        if v >= 70: return "偏空 (超买)", "bear"
        return "中性", "neutral"
    elif col == "10Y_Yield":
        if v >= 4.5: return "偏空", "bear"
        if v <= 3.8: return "偏多", "bull"
        return "中性", "neutral"
    elif col == "DXY":
        if v >= 100: return "偏空 (强势)", "bear"
        if v <= 97: return "偏多 (弱势)", "bull"
        return "中性", "neutral"
    elif col == "BTC_Chg":
        if v >= 3: return "大涨 (Risk On)", "bull"
        if v <= -3: return "大跌 (Risk Off)", "bear"
        return "波动正常", "neutral"
    elif col == "Risk_Ratio":
        if v >= 1.5: return "Risk On", "bull"
        if v <= 1.3: return "Risk Off", "bear"
        return "中性", "neutral"
    elif col == "SKEW":
        if v >= 150: return "尾部风险升高", "bear"
        if v <= 120: return "尾部风险低", "bull"
        return "中性", "neutral"
    elif col == "Above_200MA":
        if v >= 60: return "多头", "bull"
        if v <= 40: return "空头", "bear"
        return "中性", "neutral"
    elif col == "AAII_Diff":
        if v <= -10: return "偏多 (散户悲观)", "bull"
        if v >= 20: return "偏空 (散户乐观)", "bear"
        return "中性", "neutral"
    elif col == "Put_Call":
        if v >= 1.0: return "偏多 (看空过度)", "bull"
        if v <= 0.7: return "偏空 (看多过度)", "bear"
        return "中性", "neutral"
    elif col == "NAAIM":
        if v <= 50: return "偏多", "bull"
        if v >= 90: return "偏空", "bear"
        return "中性", "neutral"
    return "中性", "neutral"


def generate_html_from_csv():
    """Discord 风格 + 简体中文 + 涨跌幅对比 + 手机优化"""
    file = "data/history.csv"
    if not os.path.exists(file):
        print("⚠️ 找不到 history.csv")
        return

    try:
        df_hist = pd.read_csv(file)
        if df_hist.empty:
            print("⚠️ history.csv 为空")
            return

        latest = df_hist.iloc[-1]
        prev = df_hist.iloc[-2] if len(df_hist) >= 2 else None

        trade_date = _safe(latest.get("Date"))

        # 大盘涨跌幅
        spx = _safe(latest.get("SPX_Close"))
        ndx = _safe(latest.get("NDX_Close"))
        spx_chg, spx_cls = ("—", "neutral")
        ndx_chg, ndx_cls = ("—", "neutral")
        if prev is not None:
            spx_chg, spx_cls = _calc_change(latest.get("SPX_Close"), prev.get("SPX_Close"))
            ndx_chg, ndx_cls = _calc_change(latest.get("NDX_Close"), prev.get("NDX_Close"))

        # 指标定义（增加 need_chg 标记哪些需要显示涨跌幅）
        indicators = [
            # 宏观与资金
            {"col": "10Y_Yield", "name": "🇺🇸 10年债", "cat": "macro", "unit": "%", "need_chg": True},
            {"col": "DXY", "name": "💵 美元 DXY", "cat": "macro", "unit": "", "need_chg": True},
            {"col": "HYG_Price", "name": "💳 高收债 HYG", "cat": "macro", "unit": "", "need_chg": True},
            {"col": "BTC_Chg", "name": "₿ 比特币", "cat": "macro", "unit": "%", "need_chg": False},  # 本身已是涨跌幅
            # 结构与板块
            {"col": "IWM_Price", "name": "🏢 罗素2000", "cat": "struct", "unit": "", "need_chg": True},
            {"col": "SOXX_Price", "name": "⚡ 半导体 SOXX", "cat": "struct", "unit": "", "need_chg": True},
            {"col": "Risk_Ratio", "name": "⚖️ 风险胃口", "cat": "struct", "unit": "", "need_chg": True},
            # 技术与情绪
            {"col": "RSI", "name": "📈 大盘 RSI", "cat": "tech", "unit": "", "need_chg": False},
            {"col": "VIX", "name": "🌪️ VIX 波动", "cat": "tech", "unit": "", "need_chg": True},
            {"col": "CNN", "name": "😱 CNN 情绪", "cat": "tech", "unit": "", "need_chg": True},
            {"col": "Above_200MA", "name": "📊 >200日线", "cat": "tech", "unit": "%", "need_chg": True},
            # 筹码与内资
            {"col": "NAAIM", "name": "🏦 机构持仓", "cat": "fund", "unit": "%", "need_chg": True},
            {"col": "SKEW", "name": "🦢 黑天鹅 SKEW", "cat": "fund", "unit": "", "need_chg": True},
            {"col": "AAII_Diff", "name": "🐂 散户 AAII", "cat": "fund", "unit": "%", "need_chg": True},
            {"col": "Put_Call", "name": "⚖️ Put/Call", "cat": "fund", "unit": "", "need_chg": True},
        ]

        # 统计多方空方
        bulls = bears = 0
        for item in indicators:
            val = _safe(latest.get(item["col"]))
            _, cls = _get_status(item["col"], val)
            if cls == "bull":
                bulls += 1
            elif cls == "bear":
                bears += 1

        if bulls > bears:
            theme = "#2ecc71"
            mood_text = "🟢 市场偏向恐慌/机会 (Risk On)"
        elif bears > bulls:
            theme = "#e74c3c"
            mood_text = "🔴 市场偏向贪婪/风险 (Risk Off)"
        else:
            theme = "#95a5a6"
            mood_text = "⚪ 市场分歧，建议观望"

        def make_section(title, cat):
            html = f'<div class="section"><div class="section-title">{title}</div>'
            for item in indicators:
                if item["cat"] != cat:
                    continue
                val = _safe(latest.get(item["col"]))
                unit = item["unit"] if val != "—" else ""
                status_text, status_cls = _get_status(item["col"], val)

                # 计算涨跌幅
                chg_html = ""
                if item["need_chg"] and prev is not None and val != "—":
                    chg_text, chg_cls = _calc_change(latest.get(item["col"]), prev.get(item["col"]))
                    chg_html = f'<span class="chg {chg_cls}">{chg_text}</span>'

                html += f'''
                <div class="item">
                    <span class="name">{item["name"]}</span>
                    <span class="val">{val}{unit}</span>
                    {chg_html}
                    <span class="status {status_cls}">{status_text}</span>
                </div>'''
            html += '</div>'
            return html

        sections = (
            make_section("🌊 宏观与资金 (Macro)", "macro") +
            make_section("🏗️ 结构与板块 (Struct)", "struct") +
            make_section("🌡️ 技术与情绪 (Tech)", "tech") +
            make_section("🐳 筹码与内资 (Fund)", "fund")
        )

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>每日财经情绪日报 - {trade_date}</title>
<style>
:root {{
  --bg: #0f1419;
  --card: #1a2332;
  --text: #e7e9ea;
  --muted: #8b98a5;
  --border: #2a3140;
  --theme: {theme};
  --bull: #2ecc71;
  --bear: #e74c3c;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.45;
  padding: 16px 12px 40px;
  max-width: 480px;
  margin: 0 auto;
}}
.header {{
  text-align: center;
  padding: 20px 12px 16px;
  border-bottom: 3px solid var(--theme);
  margin-bottom: 16px;
}}
.header h1 {{
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 4px;
}}
.header .date {{
  color: var(--muted);
  font-size: 0.9rem;
}}
.card {{
  background: var(--card);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
}}
.card-title {{
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--theme);
  margin-bottom: 10px;
}}
.summary-line {{
  font-size: 0.95rem;
  margin-bottom: 4px;
}}
.market-item {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 0.95rem;
  border-bottom: 1px solid var(--border);
}}
.market-item:last-child {{ border-bottom: none; }}
.market-left {{
  display: flex;
  flex-direction: column;
}}
.market-name {{
  color: #cfd9de;
  font-size: 0.9rem;
}}
.market-price {{
  font-weight: 600;
  font-size: 1.05rem;
}}
.chg {{
  font-size: 0.85rem;
  font-weight: 500;
  margin-left: 6px;
}}
.chg.bull {{ color: var(--bull); }}
.chg.bear {{ color: var(--bear); }}
.chg.neutral {{ color: var(--muted); }}
.section {{
  background: var(--card);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
}}
.section-title {{
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}}
.item {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 9px 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.9rem;
}}
.item:last-child {{ border-bottom: none; }}
.name {{
  flex: 1 1 100px;
  color: #cfd9de;
}}
.val {{
  flex: 0 0 auto;
  font-weight: 500;
  min-width: 55px;
  text-align: right;
}}
.status {{
  flex: 0 0 auto;
  font-size: 0.82rem;
  padding: 2px 6px;
  border-radius: 4px;
}}
.status.bull {{ background: rgba(46,204,113,0.15); color: var(--bull); }}
.status.bear {{ background: rgba(231,76,60,0.15); color: var(--bear); }}
.status.neutral {{ background: rgba(149,165,166,0.15); color: #95a5a6; }}
footer {{
  text-align: center;
  color: var(--muted);
  font-size: 0.75rem;
  margin-top: 24px;
}}
</style>
</head>
<body>
  <div class="header">
    <h1>📅 每日财经情绪日报</h1>
    <div class="date">{trade_date}</div>
  </div>

  <div class="card">
    <div class="card-title">🔮 市场情绪总结</div>
    <div class="summary-line">🟢 多方: {bulls}　|　🔴 空方: {bears}</div>
    <div class="summary-line">{mood_text}</div>
  </div>

  <div class="card">
    <div class="card-title">📊 美股大盘指数</div>
    <div class="market-item">
      <div class="market-left">
        <span class="market-name">S&P 500</span>
        <span class="market-price">{spx}</span>
      </div>
      <span class="chg {spx_cls}">{spx_chg}</span>
    </div>
    <div class="market-item">
      <div class="market-left">
        <span class="market-name">Nasdaq 100</span>
        <span class="market-price">{ndx}</span>
      </div>
      <span class="chg {ndx_cls}">{ndx_chg}</span>
    </div>
  </div>

  {sections}

  <footer>
    数据来源：history.csv　·　较上一日涨跌幅已标注<br>
    美股收盘后自动更新 · 手机友好
  </footer>
</body>
</html>
"""
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ index.html 已生成（含涨跌幅对比 · {trade_date}）")
    except Exception as e:
        print(f"❌ 生成 index.html 失败: {e}")


def save_csv(results):
    try:
        folder = "data"
        if not os.path.exists(folder):
            os.makedirs(folder)
        file = "data/history.csv"

        try:
            t = yf.Ticker("^GSPC")
            hist = t.history(period="5d")
            if not hist.empty:
                last_trade_date = hist.index[-1].strftime("%Y-%m-%d")
            else:
                last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"❌ 日期侦测失败: {e}")
            last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")

        print(f"📅 侦测到最新交易日为: {last_trade_date}")

        if os.path.exists(file):
            try:
                existing_df = pd.read_csv(file)
                if 'Date' in existing_df.columns and last_trade_date in existing_df['Date'].values.astype(str):
                    print(f"🛑 日期 {last_trade_date} 已存在，今日不写入。")
                    return last_trade_date
            except Exception as e:
                print(f"⚠️ 读取 CSV 检查错误: {e}")

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
        aaii_val = f"{aaii_raw[2]:.1f}" if isinstance(aaii_raw, tuple) and len(aaii_raw) >= 3 else extract_numeric_value(str(aaii_raw))
        row = {
            'Date': last_trade_date,
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

        file_exists = os.path.exists(file) and os.stat(file).st_size > 0
        with open(file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        print(f"💾 数据已储存至: {file}")
        return last_trade_date
    except Exception as e:
        print(f"CSV Error: {e}")
        return datetime.datetime.now().strftime("%Y-%m-%d")
