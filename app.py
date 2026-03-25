import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect

# --- CONFIG ---
st.set_page_config(page_title="TradingScreener - Live Dashboard", layout="wide", page_icon="📈")

# --- STOCKS DATABASE (Top 4 for each to keep it clean) ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}, {"s": "PVRINOX-EQ", "t": "13147"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}, {"s": "EICHERMOT-EQ", "t": "910"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}]
}

# --- FUNCTIONS ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = api.generateSession(client_id, password, token)
        return api if res['status'] else None
    except: return None

def get_market_sentiment(api):
    indices = {"NIFTY 50": "99926000", "NIFTY PSU BANK": "99926008", "NIFTY IT": "99926002", "NIFTY MEDIA": "99926006", "NIFTY AUTO": "99926001", "NIFTY METAL": "99926004"}
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
    # Filter out Nifty 50 to find best sector
    sectors_only = [x for x in perf if x['name'] != "NIFTY 50"]
    target = max(sectors_only, key=lambda x: x['change']) if mode == "BUY" else min(sectors_only, key=lambda x: x['change'])
    return mode, target['name'], nifty

def create_chart(df, symbol, pdh, pdl):
    # Calculate EMA 10 (The Orange Line)
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    
    fig = go.Figure()
    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'],
        name="Price", increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    ))
    # EMA 10 Line
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10 (Exit Line)"))
    
    # Horizontal Levels (PDH/PDL)
    fig.add_hline(y=pdh, line_dash="dash", line_color="#00ff00", annotation_text="Prev Day High")
    fig.add_hline(y=pdl, line_dash="dash", line_color="#ff0000", annotation_text="Prev Day Low")
    
    fig.update_layout(
        title=f"{symbol} (5 Min Chart)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

# --- UI ---
with st.sidebar:
    st.title("🔑 Login Details")
    u_api = st.text_input("API Key", type="password")
    u_id = st.text_input("Client ID")
    u_pwd = st.text_input("Password", type="password")
    u_totp = st.text_input("TOTP Secret", type="password")
    u_risk = st.number_input("My Risk Per Trade (₹)", 1000)
    start = st.button("🚀 Start Live Monitoring")

st.title("🛡️ Pro Strategy Screener")

if not start:
    st.info("Please enter your credentials in the sidebar and click Start.")
else:
    api = login(u_api, u_id, u_pwd, u_totp)
    if not api:
        st.error("Login Failed! Please check your API Key and TOTP.")
    else:
        # Initial scan
        mode, sector, nifty_p = get_market_sentiment(api)
        
        # Display Stats
        m1, m2, m3 = st.columns(3)
        m1.metric("Market Sentiment", mode, f"{nifty_p:.2f}% Nifty")
        m2.metric("Target Sector", sector)
        m3.write(f"🔄 Last Updated: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        st.divider()

        # Infinite Loop
        while True:
            stocks = STOCKS_DB.get(sector, [])
            
            for s in stocks:
                # 1. Fetch Previous Day High/Low
                to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                from_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                hist = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date})
                
                if hist['status'] and len(hist['data']) >= 2:
                    pdh, pdl = hist['data'][-2][2], hist['data'][-2][3]
                    
                    # 2. Fetch Live 5-Min Candles
                    today_0915 = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                    candles = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": today_0915, "todate": to_date})
                    
                    if candles['status'] and candles['data']:
                        df = pd.DataFrame(candles['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                        
                        # 3. Strategy Logic Check
                        signal = None
                        for i in range(len(df)-1):
                            c1, c2 = df.iloc[i], df.iloc[i+1]
                            # Master Candle Breakout Check
                            is_master = (mode=="BUY" and c1['c'] > pdh) or (mode=="SELL" and c1['c'] < pdl)
                            if is_master and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 3.0:
                                # Confirmation Candle Check
                                if mode=="BUY" and c2['c'] > c2['o'] and c2['l'] >= c1['l']:
                                    risk = abs(c2['c'] - c2['l'])
                                    if (risk/c2['c'])*100 <= 1.0:
                                        signal = {"price": c2['c'], "sl": c2['l'], "qty": math.floor(u_risk/risk)}
                                elif mode=="SELL" and c2['c'] < c2['o'] and c2['h'] <= c1['h']:
                                    risk = abs(c2['h'] - c2['c'])
                                    if (risk/c2['c'])*100 <= 1.0:
                                        signal = {"price": c2['c'], "sl": c2['h'], "qty": math.floor(u_risk/risk)}

                        # 4. Render Output
                        with st.container():
                            if signal:
                                st.success(f"🎯 **SIGNAL FOUND: {s['s']}** | Entry: {signal['price']} | SL: {signal['sl']} | **Buy Qty: {signal['qty']}**")
                                st.info(f"💰 Capital Required: ₹{signal['qty'] * signal['price']:.0f}")
                            else:
                                st.write(f"🔍 Monitoring **{s['s']}** for breakout...")
                            
                            st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)
                            st.divider()

            time.sleep(60) # Refresh every minute
            st.rerun()
