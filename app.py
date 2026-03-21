import streamlit as st
import pyotp, math, datetime, time, pandas as pd
from SmartApi import SmartConnect

# --- CONFIG ---
st.set_page_config(page_title="Bazaar Ke Mahir Screener", layout="wide", page_icon="📈")

# --- DATABASE (Extended) ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}, {"s": "UNIONBANK-EQ", "t": "10245"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}, {"s": "LTIM-EQ", "t": "17818"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}, {"s": "PVRINOX-EQ", "t": "13147"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}]
}

# --- FUNCTIONS ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        totp = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        data = api.generateSession(client_id, password, totp)
        return api if data['status'] else None
    except: return None

def get_market_data(api):
    indices = {"NIFTY 50": "99926000", "NIFTY PSU BANK": "99926008", "NIFTY IT": "99926002", "NIFTY MEDIA": "99926006", "NIFTY AUTO": "99926001"}
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                change = ((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100
                perf.append({"name": name, "change": change, "ltp": d['data']['ltp']})
        except: continue
    nifty = next(i for i in perf if i["name"] == "NIFTY 50")["change"]
    mode = "BUY" if nifty > 0 else "SELL"
    target = max(perf[1:], key=lambda x: x['change']) if mode == "BUY" else min(perf[1:], key=lambda x: x['change'])
    return mode, target['name'], target['change']

# --- UI ---
st.title("🚀 Bazaar Ke Mahir - Intraday Screener")
st.caption("Automated Strategy based on Sectorial Momentum & PDH/PDL Breakouts")

with st.sidebar:
    st.header("🔐 Access")
    api_key = st.text_input("API Key", type="password")
    c_id = st.text_input("Client ID")
    pwd = st.text_input("Password", type="password")
    totp = st.text_input("TOTP Secret", type="password")
    risk = st.number_input("Risk Amount (Rs)", 1000)
    start = st.button("Start Live Scanning")

if start:
    api = login(api_key, c_id, pwd, totp)
    if not api: st.error("Login Failed")
    else:
        mode, sector, change = get_market_data(api)
        c1, c2 = st.columns(2)
        c1.metric("Market Sentiment", mode, f"{change:.2f}%")
        c2.metric("Target Sector", sector)

        st.divider()
        
        # --- SCANNING LOOP ---
        while True:
            stocks = STOCKS_DB.get(sector, [])
            active_signals = []
            watchlist_data = []

            for s in stocks:
                # 1. Levels
                to_d = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                from_d = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                hist = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_d, "todate": to_d})
                if not hist['status'] or len(hist['data']) < 2: continue
                pdh, pdl = hist['data'][-2][2], hist['data'][-2][3]

                # 2. Live Data
                today_start = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                candles = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": today_start, "todate": to_d})
                
                ltp = 0
                if candles['status'] and candles['data']:
                    df = pd.DataFrame(candles['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                    ltp = df.iloc[-1]['c']
                    
                    # Strategy Check
                    for i in range(len(df)-1):
                        c1_candle, c2_candle = df.iloc[i], df.iloc[i+1]
                        breakout = (mode == "BUY" and c1_candle['c'] > pdh) or (mode == "SELL" and c1_candle['c'] < pdl)
                        if breakout and (abs(c1_candle['c'] - c1_candle['o'])/c1_candle['o'])*100 <= 3.0:
                            if (mode=="BUY" and c2_candle['c']>c2_candle['o']) or (mode=="SELL" and c2_candle['c']<c2_candle['o']):
                                risk_val = abs(c2_candle['c'] - (c2_candle['l'] if mode=="BUY" else c2_candle['h']))
                                if (risk_val/c2_candle['c'])*100 <= 1.0:
                                    active_signals.append({"Stock": s['s'], "Price": c2_candle['c'], "SL": (c2_candle['l'] if mode=="BUY" else c2_candle['h']), "Qty": math.floor(risk/risk_val)})

                watchlist_data.append({"Stock": s['s'], "LTP": ltp, "Target Level": pdh if mode=="BUY" else pdl, "Status": "Target Crossed" if (mode=="BUY" and ltp > pdh) or (mode=="SELL" and ltp < pdl) else "Waiting"})

            # Display Signals
            if active_signals:
                st.subheader("🔥 ACTIVE SIGNALS")
                for sig in active_signals:
                    st.success(f"**{sig['Stock']}** | Entry: {sig['Price']} | SL: {sig['SL']} | **Qty: {sig['Qty']}**")
            
            # Display Watchlist
            st.subheader(f"📋 {sector} Watchlist")
            st.table(pd.DataFrame(watchlist_data))
            
            time.sleep(60)
            st.rerun()
