# --- config.py (v6.2: 彻底移除旧爬虫 & 纯 API 优化版) ---
import data_fetchers as df  # 统一使用 API 抓取器

INDICATORS = {
    # --- 1. 🌊 宏观与资金 ---
    'BOND_10Y': {
        'name': '🇺🇸 10年债', 'category': 'macro', 'type': 'custom', 'func': df.fetch_bond_10y,
        'thresholds': (3.5, 4.5), 'inverse': True
    },
    'DXY': {
        'name': '💵 美元 DXY', 'category': 'macro', 'type': 'custom', 'func': df.fetch_dxy,
        'thresholds': (101, 105), 'inverse': True
    },
    'HYG': {
        'name': '💳 高收债 HYG', 'category': 'macro', 'type': 'trend', 'ticker': 'HYG',
        'thresholds': 'ma_trend'
    },
    'BTC': {
        'name': '🪙 比特币', 'category': 'macro', 'type': 'custom', 'func': df.fetch_bitcoin_trend,
        'thresholds': (3.0, -3.0)
    },

    # --- 2. 🏗️ 结构与板块 ---
    'IWM': {
        'name': '🏢 罗素2000', 'category': 'struct', 'type': 'trend', 'ticker': 'IWM',
        'thresholds': 'ma_trend'
    },
    'SOXX': {
        'name': '⚡ 半导体 SOXX', 'category': 'struct', 'type': 'trend', 'ticker': 'SOXX',
        'thresholds': 'ma_trend'
    },
    'RISK_RATIO': {
        'name': '⚖️ 风险胃口', 'category': 'struct', 'type': 'custom', 'func': df.fetch_risk_on_off_ratio,
        'thresholds': 'arrow_trend'
    },

    # --- 3. 🌡️ 技术与情绪 ---
    'RSI': {
        'name': '📈 大盘 RSI', 'category': 'tech', 'type': 'custom', 'func': df.fetch_rsi_index,
        'thresholds': (30, 70), 'inverse': True
    },
    'VIX': {
        'name': '🌪️ VIX 波动', 'category': 'tech', 'type': 'price', 'ticker': '^VIX',
        'thresholds': (30, 15), 'inverse': False
    },
    'CNN': {
        'name': '😱 CNN 情绪', 'category': 'tech', 'type': 'external', 'func': df.fetch_cnn_index,
        'thresholds': (45, 55), 'inverse': True
    },
    'ABOVE_200_DAYS': {
        'name': '📊 >200日线', 'category': 'tech', 'type': 'custom', 'func': df.fetch_above_200ma,
        'thresholds': (20, 80), 'inverse': True
    },

    # --- 4. 🐳 筹码与内资 ---
    'NAAIM': {
        'name': '🏦 机构持仓', 'category': 'fund', 'type': 'external', 'func': df.fetch_naaim_index,
        'thresholds': (40, 90), 'inverse': True
    },
    'SKEW': {
        'name': '🦢 黑天鹅 SKEW', 'category': 'fund', 'type': 'custom', 'func': df.fetch_skew,
        'thresholds': (120, 140), 'inverse': True
    },
    'AAII': {
        'name': '🐂 散户 AAII', 'category': 'fund', 'type': 'external', 'func': df.fetch_aaii_sentiment,
        'thresholds': (-15, 15), 'inverse': True
    },
    'PUT_CALL': {
        'name': '⚖️ Put/Call', 'category': 'fund', 'type': 'custom', 'func': df.fetch_put_call_ratio,
        'thresholds': (1.0, 0.8), 'inverse': False
    }
}

IMAGES = {
    # 🟢 多方 / Risk On (例如: 牛、火箭、绿色上涨图)
    'BULL': "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExbXR6MzhxOHF2dDE1N3F4cm1nbGRqazgyMmx5dHFydnZtd2kybm5teCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/IDpoYMdXd9osK1jmyd/giphy.gif",

    # 🔴 空方 / Risk Off (例如: 熊、闪电、红色下跌图)
    'BEAR': "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaTZzd2kxd2xxOHJsNnh5Z3ljYWdjZm9iNXZuZTk5OTJqbjRzcGVxbyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/YqQ4o3QJcWRrdElNLq/giphy.gif",

    # ⚪ 中性 / 观望 (例如: 天秤、平盘)
    'NEUTRAL': "https://cdn-icons-png.flaticon.com/512/3135/3135706.png"
}