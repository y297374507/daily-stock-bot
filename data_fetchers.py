# --- data_fetchers.py (v6.3: 抗限流 & 防卡死增强版) ---
import yfinance as yf
import requests
import re
import time

# ---------------------------------------------------------------------------
# 全局请求配置 (加入 User-Agent 与 Session 绕过 Yahoo / 网页防爬与限流)
# ---------------------------------------------------------------------------
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

session = requests.Session()
session.headers.update(headers)


# ---------------------------------------------------------------------------
# 1. 大盘与行情数据 (OHLCV)
# ---------------------------------------------------------------------------

def fetch_full_market_data():
    """一次性抓取 SPX 与 NDX 的 开/高/低/收/量"""
    try:
        tickers = ["^GSPC", "^NDX"]
        data = yf.download(tickers, period="1d", progress=False, auto_adjust=False)

        result = {}
        for symbol in tickers:
            prefix = "SPX" if symbol == "^GSPC" else "NDX"
            try:
                result[f'{prefix}_Open'] = f"{data['Open'][symbol].iloc[-1]:.2f}"
                result[f'{prefix}_High'] = f"{data['High'][symbol].iloc[-1]:.2f}"
                result[f'{prefix}_Low'] = f"{data['Low'][symbol].iloc[-1]:.2f}"
                result[f'{prefix}_Close'] = f"{data['Close'][symbol].iloc[-1]:.2f}"
                result[f'{prefix}_Volume'] = f"{data['Volume'][symbol].iloc[-1]:.0f}"
            except Exception:
                result[f'{prefix}_Open'] = ""
                result[f'{prefix}_High'] = ""
                result[f'{prefix}_Low'] = ""
                result[f'{prefix}_Close'] = ""
                result[f'{prefix}_Volume'] = ""

        return result
    except Exception as e:
        print(f"❌ Market Data 抓取失败: {e}")
        return {}


def fetch_market_info():
    """抓取 S&P 500 与 Nasdaq 100 当日涨跌幅文本"""
    try:
        d = yf.download(["^GSPC", "^NDX"], period="2d", progress=False, auto_adjust=False)['Close']
        msg = []
        name_map = {"^GSPC": "S&P 500", "^NDX": "Nasdaq 100"}
        for sym in ["^GSPC", "^NDX"]:
            try:
                curr = d[sym].iloc[-1]
                prev = d[sym].iloc[-2]
                chg = (curr - prev) / prev * 100
                icon = "📈" if chg > 0 else "📉"
                display_name = name_map.get(sym, sym)
                msg.append(f"{icon} **{display_name}**: {curr:,.2f} ({chg:+.2f}%)")
            except Exception:
                pass
        return "\n".join(msg) if msg else "N/A"
    except Exception as e:
        print(f"❌ Market Info 抓取失败: {e}")
        return "N/A"


# ---------------------------------------------------------------------------
# 2. 通用 yfinance 抓取函数
# ---------------------------------------------------------------------------

def fetch_yf_price(ticker, correction=1.0):
    """通用抓取单项资产最新价格"""
    try:
        time.sleep(0.5)  # 极简缓冲，防止被 Yahoo 限流
        t = yf.Ticker(ticker)
        d = t.history(period="5d")
        if not d.empty:
            val = d['Close'].iloc[-1]
            if correction != 1.0 and val > 20:
                val = val * correction
            return f"{val:.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ Price Error [{ticker}]: {e}")
        return "N/A"


def fetch_yf_trend(ticker):
    """通用抓取 20MA 均线排列趋势 (Above / Below)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker(ticker)
        d = t.history(period="2mo")
        if len(d) >= 20:
            ma20 = d['Close'].rolling(window=20).mean().iloc[-1]
            curr = d['Close'].iloc[-1]
            status = "Above" if curr > ma20 else "Below"
            return f"{curr:.2f} ({status})"
        return "N/A"
    except Exception as e:
        print(f"❌ Trend Error [{ticker}]: {e}")
        return "N/A"


# ---------------------------------------------------------------------------
# 3. 宏观与资金指标 (Macro)
# ---------------------------------------------------------------------------

def fetch_bond_10y():
    """10年期美债收益率 (^TNX)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker("^TNX")
        d = t.history(period="5d")
        if not d.empty:
            val = d['Close'].iloc[-1]
            if val > 20: val = val / 10.0
            return f"{val:.2f}%"
        return "N/A"
    except Exception as e:
        print(f"❌ 10年美债抓取失败: {e}")
        return "N/A"


def fetch_short_term_yield():
    """3个月国库券收益率 (^IRX)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker("^IRX")
        d = t.history(period="5d")
        if not d.empty:
            val = d['Close'].iloc[-1]
            if val > 20: val = val / 10.0
            return f"{val:.2f}%"
        return "N/A"
    except Exception as e:
        print(f"❌ 3M 国库券抓取失败: {e}")
        return "N/A"


def fetch_dxy():
    """美元指数 (DX-Y.NYB / DX=F)"""
    try:
        time.sleep(0.5)
        for sym in ["DX-Y.NYB", "DX=F"]:
            t = yf.Ticker(sym)
            d = t.history(period="5d")
            if not d.empty:
                return f"{d['Close'].iloc[-1]:.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ 美元指数抓取失败: {e}")
        return "N/A"


def fetch_bitcoin_trend():
    """比特币 24H 涨跌幅"""
    try:
        time.sleep(0.5)
        d = yf.Ticker("BTC-USD").history(period="5d")
        if len(d) >= 2:
            chg = ((d['Close'].iloc[-1] - d['Close'].iloc[-2]) / d['Close'].iloc[-2]) * 100
            return f"{chg:+.2f}%"
        return "N/A"
    except Exception as e:
        print(f"❌ BTC 抓取失败: {e}")
        return "N/A"


def fetch_risk_on_off_ratio():
    """风险胃口 (XLY / XLP 比例)"""
    try:
        time.sleep(0.5)
        d = yf.download(["XLY", "XLP"], period="5d", progress=False, auto_adjust=False)['Close']
        if len(d) >= 2:
            r_now = d['XLY'].iloc[-1] / d['XLP'].iloc[-1]
            r_prev = d['XLY'].iloc[-2] / d['XLP'].iloc[-2]
            icon = "↗️" if r_now > r_prev else "↘️"
            return f"{r_now:.2f} ({icon})"
        return "N/A"
    except Exception as e:
        print(f"❌ Risk On/Off 抓取失败: {e}")
        return "N/A"


# ---------------------------------------------------------------------------
# 4. 技术与情绪指标 (Tech)
# ---------------------------------------------------------------------------

def fetch_rsi_index():
    """标普500 (SPX) 14日 RSI"""
    try:
        time.sleep(0.5)
        d = yf.Ticker("^GSPC").history(period="2mo")
        if len(d) > 14:
            delta = d['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(com=13, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(com=13, adjust=False).mean()
            rsi = 100 - (100 / (1 + (gain / loss)))
            return f"{rsi.iloc[-1]:.1f}"
        return "N/A"
    except Exception as e:
        print(f"❌ RSI 抓取失败: {e}")
        return "N/A"


def fetch_skew():
    """CBOE 黑天鹅 SKEW 指数 (^SKEW)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker("^SKEW")
        d = t.history(period="5d")
        if not d.empty:
            return f"{d['Close'].iloc[-1]:.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ SKEW 抓取失败: {e}")
        return "N/A"


def fetch_cnn_index():
    """CNN 恐慌与贪婪指数"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = session.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            score = round(data['fear_and_greed']['score'])
            return f"{score}"
        return "N/A"
    except Exception as e:
        print(f"❌ CNN 恐慌指数抓取失败: {e}")
        return "N/A"


def fetch_above_200ma():
    """标普 500 站上 200 日均线比例 (^S5TH)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker("^S5TH")
        d = t.history(period="5d")
        if not d.empty:
            return f"{d['Close'].iloc[-1]:.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ 200日线比例抓取失败: {e}")
        return "N/A"


# ---------------------------------------------------------------------------
# 5. 筹码与散户指标 (Fund)
# ---------------------------------------------------------------------------

def fetch_aaii_sentiment():
    """散户 AAII 情绪调查"""
    try:
        url = "https://www.aaii.com/sentimentsurvey/sent_results"
        r = session.get(url, timeout=5)
        if r.status_code == 200:
            bull = re.search(r'Bullish:\s*([\d\.]+)%', r.text)
            bear = re.search(r'Bearish:\s*([\d\.]+)%', r.text)
            if bull and bear:
                b_val = float(bull.group(1))
                r_val = float(bear.group(1))
                diff = b_val - r_val
                return (b_val, r_val, diff)
        return "N/A"
    except Exception as e:
        print(f"❌ AAII 抓取失败: {e}")
        return "N/A"


def fetch_naaim_index():
    """NAAIM 机构经理仓位指数 (设置 5 秒硬性超时，绝不卡死)"""
    try:
        url = "https://www.naaim.org/resources/naaim-exposure-index/"
        r = session.get(url, timeout=5, verify=False)  # verify=False 避免 SSL 握手卡死
        if r.status_code == 200:
            match = re.search(r'NAAIM Exposure Index is\s*([\d\.]+)', r.text, re.IGNORECASE)
            if match:
                return f"{float(match.group(1)):.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ NAAIM 抓取失败 (已跳过): {e}")
        return "N/A"


def fetch_put_call_ratio():
    """CBOE Put/Call 比例 (^CPC)"""
    try:
        time.sleep(0.5)
        t = yf.Ticker("^CPC")
        d = t.history(period="5d")
        if not d.empty:
            return f"{d['Close'].iloc[-1]:.2f}"
        return "N/A"
    except Exception as e:
        print(f"❌ Put/Call 抓取失败: {e}")
        return "N/A"