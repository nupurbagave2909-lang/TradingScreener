import streamlit as st
import pyotp, math, datetime, time, pandas as pd
from SmartApi import SmartConnect

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Trade Screener", layout="wide")

# --- CUSTOM CSS FOR MOBILE ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .signal-card { padding: 20px; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.title("🔑 Credentials")
    api_key = st.text_input("API Key", type="password")
    client_id = st.text_input("Client ID")
    password = st.text_input("Password", type="password")
    totp_secret = st.text_input("TOTP Secret", type="password")
    risk_amount = st.number_input("Risk Per Trade (Rs)", value=1000)
    start_btn = st.button("🚀 Start Scanning")

# --- STRATEGY LOGIC (MODIFIED FOR UI) ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        totp = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        data = api.generateSession(client_id, password, totp)
        if data['status']: return api
    except: return None

def get_market_data(api):
    # Standard Index Tokens
    indices = {"NIFTY 50": "99926000", "NIFTY PSU BANK": "99926008", "NIFTY IT": "99926002", "NIFTY METAL": "99926004", "NIFTY AUTO": "99926001"}
    performance = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                change = ((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100
                performance.append({"name": name, "change": change})
        except: continue
    
    nifty = next(i for i in performance if i["name"] == "NIFTY 50")["change"]
    mode = "BUY" if nifty > 0 else "SELL"
    target = max(performance[1:], key=lambda x: x['change']) if mode == "BUY" else min(performance[1:], key=lambda x: x['change'])
    return mode, target['name'], target['change']

# Stocks database (Add more as needed)
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}]
}

# --- MAIN UI ---
st.title("🎯 Strategy Screener")

if not start_btn:
    st.info("Enter credentials in the sidebar and click Start.")
else:
    api = login(api_key, client_id, password, totp_secret)
    if not api:
        st.error("Login Failed! Please check your credentials.")
    else:
        # Layout
        col1, col2 = st.columns(2)
        mode, sector, change = get_market_data(api)
        
        with col1:
            st.metric("Market Sentiment", mode, delta=f"{change:.2f}%")
        with col2:
            st.metric("Top Sector", sector)

        st.subheader("🔥 Live Signals")
        placeholder = st.empty()

        while True:
            stocks = STOCKS_DB.get(sector, [])
            signals = []

            for s in stocks:
                # 1. Get Day Levels
                to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                from_date = (datetime.datetime.now() - datetime.timedelta(days=4)).strftime('%Y-%m-%d %H:%M')
                d = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date})
                if not d['status'] or len(d['data']) < 2: continue
                pdh, pdl = d['data'][-2][2], d['data'][-2][3]

                # 2. Get 5min Candles
                today_start = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                c_data = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": today_start, "todate": to_date})
                
                if c_data['status'] and c_data['data']:
                    df = pd.DataFrame(c_data['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                    # Check Logic
                    for i in range(len(df)-1):
                        c1, c2 = df.iloc[i], df.iloc[i+1]
                        breakout = (mode == "BUY" and c1['c'] > pdh) or (mode == "SELL" and c1['c'] < pdl)
                        if breakout and (abs(c1['c'] - c1['o'])/c1['o'])*100 <= 3.0:
                            if (mode=="BUY" and c2['c']>c2['o']) or (mode=="SELL" and c2['c']<c2['o']):
                                risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                risk_pct = (risk/c2['c'])*100
                                if risk_pct <= 1.0:
                                    qty = math.floor(risk_amount / risk)
                                    signals.append({
                                        "Stock": s['s'], "Price": c2['c'], 
                                        "SL": c2['l'] if mode=="BUY" else c2['h'],
                                        "Qty": qty
                                    })
            
            with placeholder.container():
                if not signals:
                    st.write("No active signals yet. Scanning every 60 seconds...")
                else:
                    for sig in signals:
                        st.success(f"### 🚀 {sig['Stock']} - {mode} SIGNAL")
                        st.write(f"**Price:** {sig['Price']} | **Stop Loss:** {sig['SL']} | **Quantity:** {sig['Qty']}")
            
            time.sleep(60) # Refresh data every minute
            st.rerun()
