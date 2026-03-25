import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pytz

# --- CONFIG ---
st.set_page_config(page_title="Pro Strategy Dashboard", layout="wide", page_icon="📈")
IST = pytz.timezone('Asia/Kolkata')

# --- STOCKS DATABASE ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY BANK": [{"s": "HDFCBANK-EQ", "t": "1333"}, {"s": "ICICIBANK-EQ", "t": "4963"}, {"s": "AXISBANK-EQ", "t": "591"}, {"s": "KOTAKBANK-EQ", "t": "1922"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}, {"s": "BAJAJ-AUTO-EQ", "t": "16669"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}]
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
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Candles"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=1.5), name="EMA-10"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="#00ff00", annotation_text="PDH")
    fig.add_hline(y=pdl, line_dash="dash", line_color="#ff0000", annotation_text="PDL")
    
    # Force X-Axis to show from 9:15 to current time
    now_ist = datetime.datetime.now(IST)
    fig.update_xaxes(range=[now_ist.strftime('%Y-%m-%d 09:15'), now_ist.strftime('%Y-%m-%d 15:30')])
    
    fig.update_layout(title=f"{symbol} (Live IST)", xaxis_rangeslider_visible=False, template="plotly_dark", height=400, margin=dict(l=10,r=10,t=30,b=10))
    return fig

# --- UI ---
with st.sidebar:
    st.title("🔐 Login")
    u_api, u_id = st.text_input("API Key", type="password"), st.text_input("Client ID")
    u_pwd, u_totp = st.text_input("Password", type="password"), st.text_input("TOTP Secret", type="password")
    u_risk = st.number_input("Risk Amount (₹)", 1000)
    user_sec = st.selectbox("Choose Sector", ["Auto-Detect"] + list(STOCKS_DB.keys()))
    start = st.button("🚀 Start Scanning")

if start:
    api = login(u_api, u_id, u_pwd, u_totp)
    if not api: st.error("Login Failed")
    else:
        while True:
            mode, auto_s, nifty_p, sector_df = get_sector_performance(api)
            final_sector = auto_s if user_sec == "Auto-Detect" else user_sec
            
            # 1. METRICS ROW
            c1, c2, c3 = st.columns(3)
            c1.metric("Market Sentiment", mode, f"{nifty_p}%")
            c2.metric("Scanning Sector", final_sector)
            c3.write(f"🇮🇳 India Time: {datetime.datetime.now(IST).strftime('%H:%M:%S')}")

            # 2. BLUE BAR CHART (Sector Comparison)
            st.subheader("📊 Sector Relative Performance")
            fig_bar = go.Figure(go.Bar(x=sector_df['Sector'], y=sector_df['Change %'], marker_color='royalblue'))
            fig_bar.update_layout(template="plotly_dark", height=250, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # 3. STOCK CHARTS
            stocks = STOCKS_DB.get(final_sector, [])
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        now_ist = datetime.datetime.now(IST)
                        # Fetch Day Levels
                        from_d = (now_ist - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                        to_d = now_ist.strftime('%Y-%m-%d %H:%M')
                        hist = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_d, "todate": to_d})
                        
                        if hist['status'] and len(hist['data']) >= 2:
                            pdh, pdl = hist['data'][-2][2], hist['data'][-2][3]
                            start_0915 = now_ist.strftime('%Y-%m-%d 09:15')
                            candles = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": start_0915, "todate": to_d})
                            
                            if candles['status'] and candles['data']:
                                df = pd.DataFrame(candles['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                                
                                # Signal Check
                                signal = None
                                if len(df) >= 2:
                                    c1, c2 = df.iloc[-2], df.iloc[-1]
                                    is_break = (mode=="BUY" and c1['c'] > pdh) or (mode=="SELL" and c1['c'] < pdl)
                                    if is_break and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 3.0:
                                        risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                        if risk > 0 and (risk/c2['c'])*100 <= 1.0:
                                            signal = {"qty": math.floor(u_risk/risk)}

                                with cols[j]:
                                    if signal: st.success(f"🎯 SIGNAL: {s['s']} | Buy Qty: {signal['qty']}")
                                    else: st.write(f"🔍 Monitoring **{s['s']}**")
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
