import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pytz
from streamlit_lottie import st_lottie
import requests

# --- CONFIG ---
st.set_page_config(page_title="Pro TradingStrategy ", layout="wide", page_icon="⚡")
IST = pytz.timezone('Asia/Kolkata')

# --- ANIMATION LOADER ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

# Animation URLs
lottie_scanning = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_6m9msh6y.json") # Pulse
lottie_success = load_lottieurl("https://assets3.lottiefiles.com/packages/lf20_ati6v960.json") # Rocket

# --- CUSTOM ANIMATED CSS ---
st.markdown("""
    <style>
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(38, 166, 154, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(38, 166, 154, 0); }
        100% { box-shadow: 0 0 0 0 rgba(38, 166, 154, 0); }
    }
    .stSuccess {
        animation: pulse 2s infinite;
        border: 2px solid #26a69a !important;
    }
    .css-1kyxreq {
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- STOCKS DATABASE ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY BANK": [{"s": "HDFCBANK-EQ", "t": "1333"}, {"s": "ICICIBANK-EQ", "t": "4963"}, {"s": "AXISBANK-EQ", "t": "591"}, {"s": "KOTAKBANK-EQ", "t": "1922"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}]
}

# --- LOGIC ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = api.generateSession(client_id, password, token)
        return api if res['status'] else None
    except: return None

def get_sector_performance(api):
    indices = {"NIFTY 50": "99926000", "NIFTY BANK": "99926009", "NIFTY IT": "99926002", "NIFTY METAL": "99926004", "NIFTY AUTO": "99926001", "NIFTY PSU BANK": "99926008", "NIFTY MEDIA": "99926006"}
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                chg = round(((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100, 2)
                perf.append({"Sector": name, "Change %": chg})
        except: continue
    df = pd.DataFrame(perf)
    nifty_chg = df[df['Sector'] == 'NIFTY 50']['Change %'].values[0]
    mode = "BUY" if nifty_chg > 0 else "SELL"
    others = df[df['Sector'] != 'NIFTY 50']
    auto_sec = others.loc[others['Change %'].idxmax()]['Sector'] if mode == "BUY" else others.loc[others['Change %'].idxmin()]['Sector']
    return mode, auto_sec, nifty_chg, df

def create_chart(df, symbol, pdh, pdl):
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="#00ff00", annotation_text="PDH")
    fig.add_hline(y=pdl, line_dash="dash", line_color="#ff0000", annotation_text="PDL")
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=30,b=0), xaxis_rangeslider_visible=False)
    return fig

# --- UI ---
with st.sidebar:
    st.title("🛡️ Trader Login")
    u_api = st.text_input("API Key", type="password")
    u_id = st.text_input("Client ID")
    u_pwd = st.text_input("Password", type="password")
    u_totp = st.text_input("TOTP Secret", type="password")
    u_risk = st.number_input("Risk Per Trade (₹)", 1000)
    user_sec = st.selectbox("Market Sector", ["Auto-Detect"] + list(STOCKS_DB.keys()))
    start = st.button("🚀 GO LIVE")

if not start:
    st_lottie(lottie_scanning, height=300)
    st.center_header = st.markdown("<h2 style='text-align: center;'>Waiting for Launch...</h2>", unsafe_allow_html=True)
else:
    api = login(u_api, u_id, u_pwd, u_totp)
    if not api: st.error("Login Failed")
    else:
        while True:
            mode, auto_s, nifty_p, sector_df = get_sector_performance(api)
            final_sector = auto_s if user_sec == "Auto-Detect" else user_sec
            
            # Header
            c1, c2, c3 = st.columns([1,1,1])
            with c1: st.metric("NIFTY 50", mode, f"{nifty_p}%")
            with c2: st.metric("FOCUS SECTOR", final_sector)
            with c3: 
                st_lottie(lottie_scanning, height=80, key="mini_scan")
                st.caption(f"Last Refresh: {datetime.datetime.now(IST).strftime('%H:%M:%S')}")

            # Sector Chart
            st.subheader("📊 Sector Momentum")
            fig_bar = go.Figure(go.Bar(x=sector_df['Sector'], y=sector_df['Change %'], marker_color='royalblue'))
            fig_bar.update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_bar, use_container_width=True)

            # Scanning
            stocks = STOCKS_DB.get(final_sector, [])
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        now_ist = datetime.datetime.now(IST)
                        # Fetch Data
                        h_res = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": (now_ist - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M'), "todate": now_ist.strftime('%Y-%m-%d %H:%M')})
                        if h_res['status'] and len(h_res['data']) >= 2:
                            pdh, pdl = h_res['data'][-2][2], h_res['data'][-2][3]
                            c_res = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": now_ist.strftime('%Y-%m-%d 09:15'), "todate": now_ist.strftime('%Y-%m-%d %H:%M')})
                            
                            if c_res['status'] and c_res['data']:
                                df = pd.DataFrame(c_res['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                                signal = None
                                if len(df) >= 2:
                                    c1, c2 = df.iloc[-2], df.iloc[-1]
                                    is_break = (mode=="BUY" and c1['c'] > pdh) or (mode=="SELL" and c1['c'] < pdl)
                                    if is_break and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 3.0:
                                        risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                        if risk > 0 and (risk/c2['c'])*100 <= 1.0:
                                            signal = {"qty": math.floor(u_risk/risk)}

                                with cols[j]:
                                    if signal:
                                        st_lottie(lottie_success, height=100, key=f"rocket_{s['s']}")
                                        st.success(f"🔥 SIGNAL FOUND: {s['s']} | QTY: {signal['qty']}")
                                    else:
                                        st.write(f"🔎 Scanning {s['s']}...")
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
