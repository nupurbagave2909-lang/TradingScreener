import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect

# --- CONFIG ---
st.set_page_config(page_title="TradingScreener - Multi-Sector Dashboard", layout="wide", page_icon="🏦")

# --- STOCKS DATABASE (Comprehensive List) ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}, {"s": "PVRINOX-EQ", "t": "13147"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}, {"s": "BAJAJ-AUTO-EQ", "t": "16669"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}],
    "NIFTY PHARMA": [{"s": "SUNPHARMA-EQ", "t": "3351"}, {"s": "CIPLA-EQ", "t": "694"}, {"s": "DRREDDY-EQ", "t": "881"}]
}

# --- LOGIC FUNCTIONS ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = api.generateSession(client_id, password, token)
        return api if res['status'] else None
    except: return None

def get_market_sentiment(api):
    indices = {"NIFTY 50": "99926000", "NIFTY PSU BANK": "99926008", "NIFTY IT": "99926002", "NIFTY MEDIA": "99926006", "NIFTY AUTO": "99926001", "NIFTY METAL": "99926004", "NIFTY PHARMA": "99926005"}
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                change = ((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100
                perf.append({"name": name, "change": change})
        except: continue
    
    nifty = next(i for i in perf if i["name"] == "NIFTY 50")["change"]
    mode = "BUY" if nifty > 0 else "SELL"
    # Logic to find the mathematically "best" sector
    sectors_only = [x for x in perf if x['name'] != "NIFTY 50"]
    auto_target = max(sectors_only, key=lambda x: x['change']) if mode == "BUY" else min(sectors_only, key=lambda x: x['change'])
    return mode, auto_target['name'], nifty

def create_chart(df, symbol, pdh, pdl):
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10 (Exit)"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="green", annotation_text="Yesterday High")
    fig.add_hline(y=pdl, line_dash="dash", line_color="red", annotation_text="Yesterday Low")
    fig.update_layout(title=f"{symbol}", yaxis_title="Price", xaxis_rangeslider_visible=False, template="plotly_dark", height=450)
    return fig

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("🛡️ Secure Access")
    u_api = st.text_input("API Key", type="password")
    u_id = st.text_input("Client ID")
    u_pwd = st.text_input("Password", type="password")
    u_totp = st.text_input("TOTP Secret", type="password")
    st.divider()
    st.header("⚙️ Settings")
    u_risk = st.number_input("Risk Per Trade (₹)", 1000)
    
    # NEW FEATURE: SELECT SECTOR
    sector_options = ["Auto-Detect Best"] + list(STOCKS_DB.keys())
    user_sector_choice = st.selectbox("Choose Sector to Scan", sector_options)
    
    start = st.button("🚀 Start Live Scanning")

# --- MAIN DASHBOARD ---
st.title("📈 Pro Strategy Dashboard")

if not start:
    st.info("👈 Please enter your details and select a sector in the sidebar.")
else:
    api = login(u_api, u_id, u_pwd, u_totp)
    if not api:
        st.error("Login Failed! Please check your credentials.")
    else:
        # Run market logic
        mode, auto_sector, nifty_p = get_market_sentiment(api)
        
        # Decide which sector to show
        final_sector = auto_sector if user_sector_choice == "Auto-Detect Best" else user_sector_choice
        
        # Top Metrics Bar
        c1, c2, c3 = st.columns(3)
        c1.metric("Nifty Sentiment", mode, f"{nifty_p:.2f}%")
        c2.metric("Active Sector", final_sector)
        c3.write(f"⏰ Server Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        st.divider()

        # Monitoring Loop
        while True:
            stocks = STOCKS_DB.get(final_sector, [])
            
            # Show a grid of charts (2 charts per row)
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        
                        # 1. Fetch Levels
                        to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                        from_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                        hist = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date})
                        
                        if hist['status'] and len(hist['data']) >= 2:
                            pdh, pdl = hist['data'][-2][2], hist['data'][-2][3]
                            
                            # 2. Fetch Live Candles
                            t_0915 = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                            candles = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": t_0915, "todate": to_date})
                            
                            if candles['status'] and candles['data']:
                                df = pd.DataFrame(candles['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                                
                                # Logic Check for Signal
                                signal = None
                                if len(df) >= 2:
                                    c1_candle, c2_candle = df.iloc[-2], df.iloc[-1]
                                    is_break = (mode=="BUY" and c1_candle['c'] > pdh) or (mode=="SELL" and c1_candle['c'] < pdl)
                                    if is_break and (abs(c1_candle['c']-c1_candle['o'])/c1_candle['o'])*100 <= 3.0:
                                        risk = abs(c2_candle['c'] - (c2_candle['l'] if mode=="BUY" else c2_candle['h']))
                                        if risk > 0: signal = {"qty": math.floor(u_risk/risk), "price": c2_candle['c'], "sl": (c2_candle['l'] if mode=="BUY" else c2_candle['h'])}

                                with cols[j]:
                                    if signal:
                                        st.success(f"🔥 SIGNAL: {s['s']} | Qty: {signal['qty']}")
                                        st.caption(f"Entry: {signal['price']} | SL: {signal['sl']}")
                                    else:
                                        st.write(f"🔍 Monitoring **{s['s']}**")
                                    
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
