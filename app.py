import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pytz
from streamlit_lottie import st_lottie
import requests

# --- CONFIG ---
st.set_page_config(page_title="Pro Trading Strategy", layout="wide", page_icon="📈")
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
    "NIFTY BANK": [
        {"s": "HDFCBANK-EQ", "t": "1333"}, {"s": "ICICIBANK-EQ", "t": "4963"}, {"s": "AXISBANK-EQ", "t": "591"}, 
        {"s": "KOTAKBANK-EQ", "t": "1922"}, {"s": "SBIN-EQ", "t": "3045"}, {"s": "INDUSINDBK-EQ", "t": "5258"},
        {"s": "AUBANK-EQ", "t": "21238"}, {"s": "FEDERALBNK-EQ", "t": "1023"}, {"s": "IDFCFIRSTB-EQ", "t": "11184"},
        {"s": "BANDHANBNK-EQ", "t": "2263"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"},
        {"s": "CANBK-EQ", "t": "10791"}, {"s": "UNIONBANK-EQ", "t": "10245"}, {"s": "IDBI-EQ", "t": "1515"},
        {"s": "INDIANB-EQ", "t": "11403"}, {"s": "UCOBANK-EQ", "t": "3688"}, {"s": "BANKINDIA-EQ", "t": "482"}
    ],
    "NIFTY IT": [
        {"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, 
        {"s": "WIPRO-EQ", "t": "3787"}, {"s": "TECHM-EQ", "t": "13538"}, {"s": "LTIM-EQ", "t": "17818"},
        {"s": "COFORGE-EQ", "t": "11543"}, {"s": "MPHASIS-EQ", "t": "4503"}, {"s": "PERSISTENT-EQ", "t": "18365"},
        {"s": "LTTS-EQ", "t": "18564"}, {"s": "TATAELXSI-EQ", "t": "3518"}, {"s": "KPITTECH-EQ", "t": "20324"}
    ],
    "NIFTY AUTO": [
        {"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}, 
        {"s": "BAJAJ-AUTO-EQ", "t": "16669"}, {"s": "EICHERMOT-EQ", "t": "910"}, {"s": "TVSMOTOR-EQ", "t": "8442"},
        {"s": "HEROMOTOCO-EQ", "t": "1348"}, {"s": "ASHOKLEY-EQ", "t": "212"}, {"s": "APOLLOTYRE-EQ", "t": "163"},
        {"s": "BHARATFORG-EQ", "t": "422"}, {"s": "MRF-EQ", "t": "2277"}, {"s": "BALKRISIND-EQ", "t": "335"}
    ],
    "NIFTY METAL": [
        {"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "JSWSTEEL-EQ", "t": "3506"}, {"s": "HINDALCO-EQ", "t": "1363"}, 
        {"s": "VEDL-EQ", "t": "3063"}, {"s": "JINDALSTEL-EQ", "t": "1727"}, {"s": "SAIL-EQ", "t": "2963"},
        {"s": "NMDC-EQ", "t": "15332"}, {"s": "NATIONALUM-EQ", "t": "6364"}, {"s": "HINDCOPPER-EQ", "t": "1370"}
    ],
    "NIFTY PHARMA": [
        {"s": "SUNPHARMA-EQ", "t": "3351"}, {"s": "CIPLA-EQ", "t": "694"}, {"s": "DRREDDY-EQ", "t": "881"}, 
        {"s": "DIVISLAB-EQ", "t": "10940"}, {"s": "APOLLOHOSP-EQ", "t": "157"}, {"s": "LUPIN-EQ", "t": "10440"},
        {"s": "AUROPHARMA-EQ", "t": "275"}, {"s": "BIOCON-EQ", "t": "11373"}, {"s": "ZYDUSLIFE-EQ", "t": "1327"}
    ],
    "NIFTY ENERGY/OIL": [
        {"s": "RELIANCE-EQ", "t": "2885"}, {"s": "ONGC-EQ", "t": "2475"}, {"s": "NTPC-EQ", "t": "11630"}, 
        {"s": "POWERGRID-EQ", "t": "14977"}, {"s": "BPCL-EQ", "t": "526"}, {"s": "COALINDIA-EQ", "t": "20371"},
        {"s": "GAIL-EQ", "t": "1232"}, {"s": "ADANIGREEN-EQ", "t": "20005"}, {"s": "TATAPOWER-EQ", "t": "3426"}
    ],
    "NIFTY REALTY": [
        {"s": "DLF-EQ", "t": "14732"}, {"s": "LODHA-EQ", "t": "4306"}, {"s": "GODREJPROP-EQ", "t": "17875"}, 
        {"s": "OBEROIRLTY-EQ", "t": "20249"}, {"s": "PHOENIXLTD-EQ", "t": "2465"}, {"s": "BRIGADE-EQ", "t": "15543"}
    ],
    "NIFTY MEDIA": [
        {"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "PVRINOX-EQ", "t": "13147"},
        {"s": "SAREGAMA-EQ", "t": "1546"}, {"s": "NETWORK18-EQ", "t": "14413"}, {"s": "TV18BRDCST-EQ", "t": "14282"}
    ],
    "NIFTY FMCG": [
        {"s": "HINDUNILVR-EQ", "t": "1330"}, {"s": "ITC-EQ", "t": "1660"}, {"s": "NESTLEIND-EQ", "t": "17963"}, 
        {"s": "BRITANNIA-EQ", "t": "547"}, {"s": "TATACONSUM-EQ", "t": "3432"}, {"s": "GODREJCP-EQ", "t": "10099"}
    ]
}

# --- LOGIC ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = api.generateSession(client_id, password, token)
        return api if res['status'] else None
    except: return None

def get_market_data(api):
    # Added INDIA VIX Token: 99926017
    indices = {
        "NIFTY 50": "99926000", "NIFTY BANK": "99926009", "NIFTY IT": "99926002", 
        "NIFTY METAL": "99926004", "NIFTY AUTO": "99926001", "NIFTY MEDIA": "99926006",
        "INDIA VIX": "99926017"
    }
    perf = []
    vix_value = 0
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                ltp = d['data']['ltp']
                close = d['data']['close']
                chg = round(((ltp - close) / close) * 100, 2)
                if name == "INDIA VIX":
                    vix_value = ltp
                else:
                    perf.append({"Sector": name, "Change": chg})
        except: continue
    
    df = pd.DataFrame(perf)
    nifty_v = df[df['Sector'] == 'NIFTY 50']['Change'].values[0]
    mode = "BUY" if nifty_v > 0 else "SELL"
    others = df[df['Sector'] != 'NIFTY 50']
    auto_sec = others.loc[others['Change'].idxmax()]['Sector'] if mode == "BUY" else others.loc[others['Change'].idxmin()]['Sector']
    return mode, auto_sec, nifty_v, vix_value, df

def create_chart(df, symbol, pdh, pdl):
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10 (Exit)"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="#00ff00", annotation_text=f"PDH: {pdh}")
    fig.add_hline(y=pdl, line_dash="dash", line_color="#ff0000", annotation_text=f"PDL: {pdl}")
    now = datetime.datetime.now(IST)
    fig.update_xaxes(range=[now.strftime('%Y-%m-%d 09:15'), now.strftime('%Y-%m-%d 15:30')])
    fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=30,b=0), xaxis_rangeslider_visible=False)
    return fig

# --- UI ---
st.sidebar.title("🛡️ Secure Trading Login")
u_api = st.sidebar.text_input("API Key", type="password")
u_id = st.sidebar.text_input("Client ID")
u_pwd = st.sidebar.text_input("Password", type="password")
u_totp = st.sidebar.text_input("TOTP Secret", type="password")
u_risk = st.sidebar.number_input("Risk Per Trade (₹)", 1000)
u_sec = st.sidebar.selectbox("Market Sector", ["Auto-Detect"] + list(STOCKS_DB.keys()))
start = st.sidebar.button("🚀 START LIVE SCAN")

if not start:
    if lottie_scanning: st_lottie(lottie_scanning, height=300)
    st.info("👈 Enter details and click START to begin live scanning.")
else:
    api = login(u_api, u_id, u_pwd, u_totp)
    if api:
        while True:
            mode, auto_s, nifty_p, vix, sector_df = get_market_data(api)
            final_sector = auto_s if u_sec == "Auto-Detect" else u_sec
            
            # --- HEADER METRICS WITH VIX ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Nifty Mood", mode, f"{nifty_p}%")
            m2.metric("Focus Sector", final_sector)
            
            # VIX Interpretation
            vix_color = "normal"
            if vix > 20: vix_color = "inverse" # Red alert
            m3.metric("INDIA VIX (Fear)", f"{vix}", delta="High Risk" if vix > 20 else "Stable", delta_color=vix_color)
            
            m4.write(f"🇮🇳 IST: {datetime.datetime.now(IST).strftime('%H:%M:%S')}")

            # Risk Warning based on VIX
            if vix > 20:
                st.warning("⚠️ **INDIA VIX is above 20!** There's more risk (High Volatility). If possible decrease the quantity or avoid trading.")
            elif vix < 15:
                st.success("✅ **Volatility is low .** Market is stable, it's good time for trading.")

            # Blue Bar Chart
            st.subheader("📊 Sector Strengths")
            fig_bar = go.Figure(go.Bar(x=sector_df['Sector'], y=sector_df['Change'], marker_color='royalblue'))
            fig_bar.update_layout(template="plotly_dark", height=180, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_bar, use_container_width=True)

            # Scanning Grid
            stocks = STOCKS_DB.get(final_sector, [])
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        now_ist = datetime.datetime.now(IST)
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
                                    if is_break and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 2.0:
                                        risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                        if risk > 0 and (risk/c2['c'])*100 <= 1.0:
                                            signal = {"entry": c2['c'], "exit": (c2['l'] if mode=="BUY" else c2['h']), "qty": math.floor(u_risk/risk)}

                                with cols[j]:
                                    if signal:
                                        if lottie_success: st_lottie(lottie_success, height=80, key=f"rocket_{s['s']}")
                                        st.success(f"🎯 SIGNAL: {s['s']}")
                                        e1, e2, e3 = st.columns(3)
                                        e1.metric("ENTRY", f"₹{signal['entry']}")
                                        e2.metric("EXIT (SL)", f"₹{signal['exit']}")
                                        e3.metric("QTY", signal['qty'])
                                    else: st.write(f"🔎 Monitoring **{s['s']}**")
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
