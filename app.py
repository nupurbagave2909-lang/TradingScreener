import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect

# --- CONFIG ---
st.set_page_config(page_title="Pro Strategy Dashboard", layout="wide", page_icon="📈")

# --- EXTENDED STOCKS DATABASE (NIFTY 50 CATEGORIZED) ---
STOCKS_DB = {
    "NIFTY PSU BANK": [
        {"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, 
        {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}
    ],
    "NIFTY BANK": [
        {"s": "HDFCBANK-EQ", "t": "1333"}, {"s": "ICICIBANK-EQ", "t": "4963"}, 
        {"s": "AXISBANK-EQ", "t": "591"}, {"s": "KOTAKBANK-EQ", "t": "1922"},
        {"s": "INDUSINDBK-EQ", "t": "5258"}
    ],
    "NIFTY IT": [
        {"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, 
        {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"},
        {"s": "TECHM-EQ", "t": "13538"}
    ],
    "NIFTY ENERGY/OIL": [
        {"s": "RELIANCE-EQ", "t": "2885"}, {"s": "ONGC-EQ", "t": "2475"}, 
        {"s": "NTPC-EQ", "t": "11630"}, {"s": "POWERGRID-EQ", "t": "14977"}
    ],
    "NIFTY AUTO": [
        {"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, 
        {"s": "MARUTI-EQ", "t": "10999"}, {"s": "EICHERMOT-EQ", "t": "910"}
    ],
    "NIFTY METAL": [
        {"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}, 
        {"s": "HINDALCO-EQ", "t": "1363"}, {"s": "JSWSTEEL-EQ", "t": "3506"}
    ],
    "NIFTY FMCG": [
        {"s": "HINDUNILVR-EQ", "t": "1330"}, {"s": "ITC-EQ", "t": "1660"}, 
        {"s": "NESTLEIND-EQ", "t": "17963"}, {"s": "BRITANNIA-EQ", "t": "547"}
    ],
    "NIFTY MEDIA": [
        {"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, 
        {"s": "PVRINOX-EQ", "t": "13147"}
    ]
}

# --- LOGIC FUNCTIONS ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        res = api.generateSession(client_id, password, token)
        return api if res['status'] else None
    except: return None

def get_sector_data(api):
    indices = {
        "NIFTY 50": "99926000", "NIFTY BANK": "99926009", "NIFTY IT": "99926002", 
        "NIFTY METAL": "99926004", "NIFTY AUTO": "99926001", "NIFTY PSU BANK": "99926008",
        "NIFTY FMCG": "99926003", "NIFTY MEDIA": "99926006"
    }
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                change = ((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100
                perf.append({"Sector": name, "Change %": round(change, 2)})
        except: continue
    
    df = pd.DataFrame(perf)
    nifty_row = df[df['Sector'] == 'NIFTY 50']
    nifty_change = nifty_row['Change %'].values[0] if not nifty_row.empty else 0
    mode = "BUY" if nifty_change > 0 else "SELL"
    
    # Auto-target sector (best if buy, worst if sell)
    others = df[df['Sector'] != 'NIFTY 50']
    auto_sector = others.loc[others['Change %'].idxmax()]['Sector'] if mode == "BUY" else others.loc[others['Change %'].idxmin()]['Sector']
    
    return mode, auto_sector, nifty_change, df

def create_chart(df, symbol, pdh, pdl):
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price"))
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=2), name="EMA-10 (Exit)"))
    fig.add_hline(y=pdh, line_dash="dash", line_color="green", annotation_text="PDH")
    fig.add_hline(y=pdl, line_dash="dash", line_color="red", annotation_text="PDL")
    fig.update_layout(title=f"{symbol}", xaxis_rangeslider_visible=False, template="plotly_dark", height=400, margin=dict(l=10, r=10, t=30, b=10))
    return fig

# --- UI ---
with st.sidebar:
    st.title("🔑 Credentials")
    u_api = st.text_input("API Key", type="password")
    u_id = st.text_input("Client ID")
    u_pwd = st.text_input("Password", type="password")
    u_totp = st.text_input("TOTP Secret", type="password")
    st.divider()
    u_risk = st.number_input("Risk Per Trade (₹)", 1000)
    sector_options = ["Auto-Detect Best"] + list(STOCKS_DB.keys())
    user_choice = st.selectbox("Select Sector", sector_options)
    start = st.button("🚀 Start Live Scanning")

st.title("🛡️ Pro Strategy Dashboard")

if start:
    api = login(u_api, u_id, u_pwd, u_totp)
    if not api:
        st.error("Login Failed")
    else:
        while True:
            mode, auto_sec, nifty_p, sector_df = get_sector_data(api)
            target_sector = auto_sec if user_choice == "Auto-Detect Best" else user_choice
            
            # Metric Summary
            c1, c2, c3 = st.columns(3)
            c1.metric("Nifty Direction", mode, f"{nifty_p}%")
            c2.metric("Target Sector", target_sector)
            c3.write(f"⏰ Last Update: {datetime.datetime.now().strftime('%H:%M:%S')}")

            # 1. THE BAR CHART FEATURE
            st.subheader("📊 Sector Relative Strength")
            # Create a bar chart showing performance of all sectors
            fig_bar = go.Figure(go.Bar(
                x=sector_df['Sector'], y=sector_df['Change %'],
                marker_color='royalblue'
            ))
            fig_bar.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # 2. SCANNING & CANDLESTICK CHARTS
            stocks = STOCKS_DB.get(target_sector, [])
            for i in range(0, len(stocks), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(stocks):
                        s = stocks[i + j]
                        
                        # Fetch Day High/Low
                        to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                        from_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                        hist = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date})
                        
                        if hist['status'] and len(hist['data']) >= 2:
                            pdh, pdl = hist['data'][-2][2], hist['data'][-2][3]
                            
                            # Fetch Live 5-Min Candles
                            t_0915 = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                            candles = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": t_0915, "todate": to_date})
                            
                            if candles['status'] and candles['data']:
                                df = pd.DataFrame(candles['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                                
                                # Logic Check
                                signal = None
                                if len(df) >= 2:
                                    c1, c2 = df.iloc[-2], df.iloc[-1]
                                    is_break = (mode=="BUY" and c1['c'] > pdh) or (mode=="SELL" and c1['c'] < pdl)
                                    if is_break and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 3.0:
                                        risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                        if risk > 0 and (risk/c2['c'])*100 <= 1.0:
                                            signal = {"qty": math.floor(u_risk/risk), "p": c2['c'], "sl": (c2['l'] if mode=="BUY" else c2['h'])}

                                with cols[j]:
                                    if signal:
                                        st.success(f"🎯 SIGNAL: {s['s']} | Qty: {signal['qty']}")
                                    else:
                                        st.write(f"🔍 Monitoring **{s['s']}**")
                                    st.plotly_chart(create_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
