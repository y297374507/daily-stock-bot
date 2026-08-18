# --- utils.py (v6.3: index.html 直接读取 CSV 最新数据渲染 + 优化排版) ---
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
    """把 nan / None / 空值 转成「暂无数据」"""
    if val is None:
        return "暂无数据"
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "n/a", "null"):
        return "暂无数据"
    return s


def generate_html_from_csv():
    """直接读取 data/history.csv 最新一行数据，生成干净的简体中文 index.html"""
    file = "data/history.csv"
    if not os.path.exists(file):
        print("⚠️ 找不到 history.csv，无法生成 index.html")
        return

    try:
        df_hist = pd.read_csv(file)
        if df_hist.empty:
            print("⚠️ history.csv 为空")
            return

        # 取最新一行
        latest = df_hist.iloc[-1]
        trade_date = _safe(latest.get("Date", datetime.datetime.now().strftime("%Y-%m-%d")))

        # 大盘数据
        spx_close = _safe(latest.get("SPX_Close"))
        ndx_close = _safe(latest.get("NDX_Close"))

        # 指标映射（CSV列名 → 显示名称 + 分类）
        indicators_map = [
            # 宏观与资金
            {"col": "10Y_Yield", "name": "🇺🇸 10年期国债收益率", "cat": "macro", "unit": "%"},
            {"col": "DXY", "name": "💵 美元指数 DXY", "cat": "macro", "unit": ""},
            {"col": "HYG_Price", "name": "💳 高收益债 HYG", "cat": "macro", "unit": ""},
            {"col": "BTC_Chg", "name": "🪙 比特币涨跌幅", "cat": "macro", "unit": "%"},
            # 结构与板块
            {"col": "IWM_Price", "name": "🏢 罗素2000 IWM", "cat": "struct", "unit": ""},
            {"col": "SOXX_Price", "name": "⚡ 半导体 SOXX", "cat": "struct", "unit": ""},
            {"col": "Risk_Ratio", "name": "⚖️ 风险胃口", "cat": "struct", "unit": ""},
            # 技术与情绪
            {"col": "RSI", "name": "📈 大盘 RSI", "cat": "tech", "unit": ""},
            {"col": "VIX", "name": "🌪️ VIX 波动率", "cat": "tech", "unit": ""},
            {"col": "CNN", "name": "😱 CNN 恐惧贪婪", "cat": "tech", "unit": ""},
            {"col": "Above_200MA", "name": "📊 站上200日线比例", "cat": "tech", "unit": "%"},
            # 筹码与内资
            {"col": "NAAIM", "name": "🏦 机构持仓 NAAIM", "cat": "fund", "unit": "%"},
            {"col": "SKEW", "name": "🦢 黑天鹅 SKEW", "cat": "fund", "unit": ""},
            {"col": "AAII_Diff", "name": "🐂 散户 AAII 净多头", "cat": "fund", "unit": "%"},
            {"col": "Put_Call", "name": "⚖️ Put/Call 比率", "cat": "fund", "unit": ""},
        ]

        # 简单情绪统计（只统计有数值的）
        bulls = 0
        bears = 0
        for item in indicators_map:
            val = latest.get(item["col"])
            if pd.isna(val) or str(val).lower() in ("nan", "n/a", ""):
                continue
            # 粗略判断（可后续再精细化）
            try:
                v = float(val)
                if item["col"] in ("VIX", "CNN") and v > 50:
                    bears += 1
                elif item["col"] in ("VIX", "CNN") and v < 30:
                    bulls += 1
                elif item["col"] == "RSI" and v > 70:
                    bears += 1
                elif item["col"] == "RSI" and v < 30:
                    bulls += 1
            except:
                pass

        if bulls > bears:
            theme_color = "#2ecc71"
            mood = "偏多 / Risk On"
        elif bears > bulls:
            theme_color = "#e74c3c"
            mood = "偏空 / Risk Off"
        else:
            theme_color = "#95a5a6"
            mood = "中性观望"

        # 生成指标 HTML
        def render_section(cat_name, cat_key):
            rows = ""
            for item in indicators_map:
                if item["cat"] != cat_key:
                    continue
                val = _safe(latest.get(item["col"]))
                unit = item["unit"] if val != "暂无数据" else ""
                rows += f"""
                <div class="row">
                    <div class="label">{item['name']}</div>
                    <div class="value">{val}{unit}</div>
                </div>
                """
            return f"""
            <section class="card">
                <h2>{cat_name}</h2>
                {rows}
            </section>
            """

        sections = (
            render_section("🌊 宏观与资金", "macro") +
            render_section("🏗️ 结构与板块", "struct") +
            render_section("🌡️ 技术与情绪", "tech") +
            render_section("🐳 筹码与内资", "fund")
        )

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日财经情绪日报 - {trade_date}</title>
    <style>
        :root {{
            --theme: {theme_color};
            --bg: #0f1419;
            --card: #1a2332;
            --text: #e7e9ea;
            --muted: #8b98a5;
            --border: #2a3140;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 20px 16px;
            max-width: 720px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            padding: 28px 16px 20px;
            border-bottom: 3px solid var(--theme);
            margin-bottom: 24px;
        }}
        header h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .sub {{
            color: var(--muted);
            font-size: 0.95rem;
        }}
        .summary {{
            background: var(--card);
            border-left: 5px solid var(--theme);
            border-radius: 10px;
            padding: 18px 20px;
            margin-bottom: 20px;
        }}
        .summary .title {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--theme);
            margin-bottom: 8px;
        }}
        .market {{
            background: var(--card);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        .market-item {{
            text-align: center;
        }}
        .market-item .name {{
            font-size: 0.85rem;
            color: var(--muted);
            margin-bottom: 4px;
        }}
        .market-item .price {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 16px;
        }}
        .card h2 {{
            font-size: 1.1rem;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }}
        .row:last-child {{
            border-bottom: none;
        }}
        .label {{
            font-size: 0.95rem;
            color: #cfd9de;
        }}
        .value {{
            font-size: 1rem;
            font-weight: 500;
            color: #ffffff;
        }}
        footer {{
            text-align: center;
            color: var(--muted);
            font-size: 0.8rem;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }}
        @media (max-width: 480px) {{
            .market {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>📅 每日财经情绪日报</h1>
        <div class="sub">交易日：{trade_date}　·　整体情绪：{mood}</div>
    </header>

    <div class="summary">
        <div class="title">🔮 市场情绪总结</div>
        <div>🟢 多方参考指标 vs 🔴 空方参考指标</div>
        <div style="margin-top:6px;">👉 {mood}</div>
    </div>

    <div class="market">
        <div class="market-item">
            <div class="name">S&P 500</div>
            <div class="price">{spx_close}</div>
        </div>
        <div class="market-item">
            <div class="name">Nasdaq 100</div>
            <div class="price">{ndx_close}</div>
        </div>
    </div>

    {sections}

    <footer>
        数据来源：history.csv 最新交易日<br>
        由 GitHub Actions 在美股收盘后自动更新
    </footer>
</body>
</html>
"""
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ index.html 已根据 CSV 最新数据生成（交易日 {trade_date}）")
    except Exception as e:
        print(f"❌ 生成 index.html 失败: {e}")


def save_csv(results):
    try:
        folder = "data"
        if not os.path.exists(folder):
            os.makedirs(folder)
        file = "data/history.csv"

        # 1. 取得市场真实交易日期
        try:
            t = yf.Ticker("^GSPC")
            hist = t.history(period="5d")
            if not hist.empty:
                last_trade_date = hist.index[-1].strftime("%Y-%m-%d")
            else:
                print("⚠️ 无法取得市场日期，使用系统日期")
                last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"❌ 日期侦测失败: {e}")
            last_trade_date = datetime.datetime.now().strftime("%Y-%m-%d")

        print(f"📅 侦测到最新交易日为: {last_trade_date}")

        # 2. 检查是否已存在该日期（防呆）
        if os.path.exists(file):
            try:
                existing_df = pd.read_csv(file)
                if 'Date' in existing_df.columns:
                    if last_trade_date in existing_df['Date'].values.astype(str):
                        print(f"🛑 日期 {last_trade_date} 已存在，今日不写入 (可能是周末或休市)。")
                        return last_trade_date
            except Exception as e:
                print(f"⚠️ 读取 CSV 检查时发生错误: {e}")

        # 3. 准备数据
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
