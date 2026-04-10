import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pytz
from streamlit_lottie import st_lottie
import requests

# --- CONFIG ---
st.set_page_config(page_title="Bazaar Ke Mahir - Live", layout="wide", page_icon="⚡")
IST = pytz.timezone('Asia/Kolkata')

# --- ANIMATION LOADER ---
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_scanning = load_lottieurl("https://lottie.host/627447e1-857e-4076-880c-03d154f67699/A7rVp8j3v9.json")
lottie_success = load_lottieurl("https://lottie.host/80407a1b-10f7-4180-8774-6869b3620942/EwZ67A5bXz.json")

# --- STOCKS DATABASE ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY BANK": [{"s": "HDFCBANK-EQ", "t": "1333"}, {"s": "ICICIBANK-EQ", "t": "4963"}, {"s": "AXISBANK-EQ", "t": "591"}, {"s": "KOTAKBANK-EQ", "t": "1922"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}]
}

# --- LOGIN WITH DYNAMIC IP DETECTION ---
def login(api_key, client_id, password, totp_secret):
    # This helps tell AngelOne which IP we are coming from dynamically
    smart_api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = smart_api.generateSession(client_id, password, token)
        if res['status']:
            return smart_api
        else:
            st.error(f"AngelOne Error: {res.get('message')}")
            return None
    except Exception as e:
        st.error(f"Login Error: {str(e)}")
        return None

def get_market_sentiment(api):
    indices = {"NIFTY 50": "99926000", "NIFTY BANK": "99926009", "NIFTY IT": "99926002", "NIFTY PSU BANK": "99926008", "NIFTY MEDIA": "99926006"}
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                chg = round(((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100, 2)
                perf.append({"Sector": name, "Change": chg})
        except: continue
    df = pd.DataFrame(perf)
    nifty_v = df[df['Sector'] == 'NIFTY 50']['Change'].values[0]
    mode = "BUY" if nifty_v > 0 else "SELL"
    others = df[df['Sector'] != 'NIFTY 50']
    auto_sec = others.loc[others['Change'].idxmax()]['Sector'] if mode == "BUY" else others.loc[others['Change'].idxmin()]['Sector']
    return mode, auto_sec, nifty_v, df

def create_chart(df, symbol, pdh, pdl):
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="green", annotation_text="Yesterday High")
    fig.add_hline(y=pdl, line_dash="dash", line_color="red", annotation_text="Yesterday Low")
    
    # Force India Market Time Window
    now = datetime.datetime.now(IST)
    fig.update_xaxes(range=[now.strftime('%Y-%m-%d 09:15'), now.strftime('%Y-%m-%d 15:30')])
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=30,b=0), xaxis_rangeslider_visible=False)
    return fig

# --- UI ---
st.title("🛡️ Bazaar Ke Mahir Pro")
st.sidebar.title("🔑 Secure Login")
u_api = st.sidebar.text_input("API Key", type="password")
u_id = st.sidebar.text_input("Client ID")
u_pwd = st.sidebar.text_input("Password", type="password")
u_totp = st.sidebar.text_input("TOTP Secret", type="password")
u_risk = st.sidebar.number_input("Risk Per Trade (₹)", 1000)
u_sector = st.sidebar.selectbox("Market Focus", ["Auto-Select"] + list(STOCKS_DB.keys()))
start = st.sidebar.button("🚀 START LIVE SCAN")

if not start:
    if lottie_scanning: st_lottie(lottie_scanning, height=300)
    st.info("Enter details in the sidebar to start live market monitoring.")
else:
    api = login(u_api, u_id, u_pwd, u_totp)
    if api:
        while True:
            mode, auto_s, nifty_p, sector_df = get_market_sentiment(api)
            final_sector = auto_s if u_sector == "Auto-Select" else u_sector
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Nifty Sentiment", mode, f"{nifty_p}%")
            c2.metric("Target Sector", final_sector)
            c3.write(f"🇮🇳 IST: {datetime.datetime.now(IST).strftime('%H:%M:%S')}")

            # Blue Sector Bar Chart
            st.subheader("📊 Sector Strengths")
            fig_bar = go.Figure(go.Bar(x=sector_df['Sector'], y=sector_df['Change'], marker_color='royalblue'))
            fig_bar.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_bar, use_container_width=True)

            # Stocks Scan
            stocks = STOCKS_DB.get(final_sector, [])
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        now_ist = datetime.datetime.now(IST)
                        h_data = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": (now_ist - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M'), "todate": now_ist.strftime('%Y-%m-%d %H:%M')})
                        if h_data['status'] and len(h_data['data']) >= 2:
                            pdh, pdl = h_data['data'][-2][2], h_data['data'][-2][3]
                            c_data = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": now_ist.strftime('%Y-%m-%d 09:15'), "todate": now_ist.strftime('%Y-%m-%d %H:%M')})
                            
                            if c_data['status'] and c_data['data']:
                                df = pd.DataFrame(c_data['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                                signal = None
                                if len(df) >= 2:
                                    c1_candle, c2_candle = df.iloc[-2], df.iloc[-1]
                                    is_break = (mode=="BUY" and c1_candle['c'] > pdh) or (mode=="SELL" and c1_candle['c'] < pdl)
                                    if is_break and (abs(c1_candle['c']-c1_candle['o'])/c1_candle['o'])*100 <= 3.0:
                                        risk = abs(c2_candle['c'] - (c2_candle['l'] if mode=="BUY" else c2_candle['h']))
                                        if risk > 0 and (risk/c2_candle['c'])*100 <= 1.0:
                                            signal = {"qty": math.floor(u_risk/risk)}

                                with cols[j]:
                                    if signal:
                                        if lottie_success: st_lottie(lottie_success, height=80, key=f"rocket_{s['s']}")
                                        st.success(f"🔥 SIGNAL: {s['s']} | QTY: {signal['qty']}")
                                    else: st.write(f"🔎 Monitoring **{s['s']}**")
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
