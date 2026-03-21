import streamlit as st
import pyotp, math, datetime, time, pandas as pd
import plotly.graph_objects as go
from SmartApi import SmartConnect

# --- CONFIG ---
st.set_page_config(page_title="Bazaar Ke Mahir - Pro Dashboard", layout="wide", page_icon="📊")

# --- STOCKS DATABASE ---
STOCKS_DB = {
    "NIFTY PSU BANK": [{"s": "SBIN-EQ", "t": "3045"}, {"s": "PNB-EQ", "t": "10666"}, {"s": "BANKBARODA-EQ", "t": "467"}, {"s": "CANBK-EQ", "t": "10791"}],
    "NIFTY IT": [{"s": "TCS-EQ", "t": "11536"}, {"s": "INFY-EQ", "t": "1594"}, {"s": "HCLTECH-EQ", "t": "2324"}, {"s": "WIPRO-EQ", "t": "3787"}],
    "NIFTY MEDIA": [{"s": "ZEEL-EQ", "t": "583"}, {"s": "SUNTV-EQ", "t": "13404"}, {"s": "SAREGAMA-EQ", "t": "1546"}],
    "NIFTY AUTO": [{"s": "TATAMOTORS-EQ", "t": "3456"}, {"s": "M&M-EQ", "t": "2031"}, {"s": "MARUTI-EQ", "t": "10999"}],
    "NIFTY METAL": [{"s": "TATASTEEL-EQ", "t": "3499"}, {"s": "VEDL-EQ", "t": "3063"}]
}

# --- LOGIC FUNCTIONS ---
def login(api_key, client_id, password, totp_secret):
    api = SmartConnect(api_key=api_key)
    try:
        token = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        data = api.generateSession(client_id, password, token)
        return api if data['status'] else None
    except: return None

def get_all_sectors(api):
    indices = {"NIFTY 50": "99926000", "NIFTY PSU BANK": "99926008", "NIFTY IT": "99926002", "NIFTY MEDIA": "99926006", "NIFTY AUTO": "99926001", "NIFTY METAL": "99926004"}
    perf = []
    for name, token in indices.items():
        try:
            d = api.ltpData("NSE", name, token)
            if d['status']:
                change = ((d['data']['ltp'] - d['data']['close']) / d['data']['close']) * 100
                perf.append({"Sector": name, "Change %": round(change, 2)})
        except: continue
    df = pd.DataFrame(perf)
    nifty_v = df[df['Sector'] == 'NIFTY 50']['Change %'].values[0]
    mode = "BUY" if nifty_v > 0 else "SELL"
    # Find top/bottom excluding Nifty 50
    other_sectors = df[df['Sector'] != 'NIFTY 50']
    target_row = other_sectors.loc[other_sectors['Change %'].idxmax()] if mode == "BUY" else other_sectors.loc[other_sectors['Change %'].idxmin()]
    return mode, target_row['Sector'], nifty_v, df

def plot_chart(df, symbol, pdh, pdl):
    # Calculate EMA 10
    df['ema10'] = df['c'].ewm(span=10, adjust=False).mean()
    
    fig = go.Figure(data=[go.Candlestick(x=df['ts'], open=df['o'], high=df['h'], low=df['l'], close=df['c'], name="Price")])
    
    # Add EMA Line
    fig.add_trace(go.Scatter(x=df['ts'], y=df['ema10'], line=dict(color='orange', width=1), name="EMA 10 (Exit Line)"))
    
    # Add PDH/PDL Lines
    fig.add_hline(y=pdh, line_dash="dash", line_color="green", annotation_text="Prev Day High")
    fig.add_hline(y=pdl, line_dash="dash", line_color="red", annotation_text="Prev Day Low")
    
    fig.update_layout(title=f"Live Analysis: {symbol}", yaxis_title="Price", xaxis_rangeslider_visible=False, height=400, template="plotly_dark")
    return fig

# --- UI START ---
st.sidebar.header("🔑 Trader Login")
api_key = st.sidebar.text_input("API Key", type="password")
client_id = st.sidebar.text_input("Client ID")
password = st.sidebar.text_input("Password", type="password")
totp = st.sidebar.text_input("TOTP Secret", type="password")
risk_val = st.sidebar.number_input("Risk Amount (Rs)", 1000)
run = st.sidebar.button("Start Live Screener")

if not run:
    st.info("👈 Enter Angel One API details and click Start to begin.")
else:
    api = login(api_key, client_id, password, totp)
    if not api:
        st.error("Login Failed. Check credentials/TOTP.")
    else:
        # Dashboard Loop
        while True:
            mode, top_sector, nifty_pct, all_sectors_df = get_all_sectors(api)
            
            # Header Row
            c1, c2, c3 = st.columns(3)
            c1.metric("Market Mode", mode, f"{nifty_pct}% Nifty")
            c2.metric("Target Sector", top_sector)
            c3.write(f"⏱️ Last Update: {datetime.datetime.now().strftime('%H:%M:%S')}")

            # Sector Comparison Chart
            st.subheader("📊 Sector Performance")
            st.bar_chart(all_sectors_df.set_index('Sector'))

            # Main Analysis
            st.divider()
            stocks = STOCKS_DB.get(top_sector, [])
            
            for s in stocks:
                # 1. Fetch Data
                to_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                from_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
                
                # Daily for levels
                h_data = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date})
                if not h_data['status'] or len(h_data['data']) < 2: continue
                pdh, pdl = h_data['data'][-2][2], h_data['data'][-2][3]

                # 5-min for live
                start_0915 = datetime.datetime.now().strftime('%Y-%m-%d 09:15')
                c_data = api.getCandleData({"exchange": "NSE", "symboltoken": s['t'], "interval": "FIVE_MINUTE", "fromdate": start_0915, "todate": to_date})
                
                if c_data['status'] and c_data['data']:
                    df = pd.DataFrame(c_data['data'], columns=['ts', 'o', 'h', 'l', 'c', 'v'])
                    ltp = df.iloc[-1]['c']
                    
                    # Logic Check
                    signal_found = False
                    for i in range(len(df)-1):
                        c1, c2 = df.iloc[i], df.iloc[i+1]
                        breakout = (mode=="BUY" and c1['c']>pdh) or (mode=="SELL" and c1['c']<pdl)
                        if breakout and (abs(c1['c']-c1['o'])/c1['o'])*100 <= 3.0:
                            if (mode=="BUY" and c2['c']>c2['o']) or (mode=="SELL" and c2['c']<c2['o']):
                                risk = abs(c2['c'] - (c2['l'] if mode=="BUY" else c2['h']))
                                if (risk/c2['c'])*100 <= 1.0:
                                    signal_found = True
                                    st.success(f"🔥 SIGNAL: {s['s']} | Action: {mode} | Qty: {math.floor(risk_val/risk)}")
                                    st.plotly_chart(plot_chart(df, s['s'], pdh, pdl), use_container_width=True)
                    
                    if not signal_found and ((mode=="BUY" and ltp > pdh*0.99) or (mode=="SELL" and ltp < pdl*1.01)):
                        st.info(f"👀 Watching {s['s']} - Near Breakout Level")
                        st.plotly_chart(plot_chart(df, s['s'], pdh, pdl), use_container_width=True)

            time.sleep(60)
            st.rerun()
