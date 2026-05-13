import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURATION & THEME ---
st.set_page_config(page_title="Portfolio Architektur Pro", layout="wide")

# Zentrales CSS für Lesbarkeit und Box-Design
st.markdown("""
    <style>
    /* Hintergrund der KPI Boxen analog zur st.info Box */
    .custom-info-box {
        background-color: #e7f3fe; 
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 10px;
        min-height: 100px;
    }
    .custom-info-box h3 {
        margin: 0;
        font-size: 14px;
        color: #1f77b4;
    }
    .custom-info-box p {
        margin: 0;
        font-size: 24px;
        font-weight: bold;
        color: #000000; /* Schwarze Schrift für KPI Werte */
    }
    /* Fix für Tabellen-Lesbarkeit (Schwarzer Text) */
    [data-testid="stDataFrame"] td {
        color: black !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKTIONEN ---
@st.cache_data
def load_portfolio():
    try:
        df = pd.read_csv("Sample-Portfolio.csv", sep=';')
        df['PurchaseDate'] = pd.to_datetime(df['PurchaseDate'])
        return df
    except Exception as e:
        st.error(f"Datei 'Sample-Portfolio.csv' nicht gefunden oder fehlerhaft: {e}")
        return None

def get_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(period="8mo") # Puffer für 6M Trends
    if hist.empty: return None, None, None, None
    
    current_price = hist['Close'].iloc[-1]
    pct_change = stock.info.get('regularMarketChangePercent')
    # print(f"Veränderung: {pct_change}%")

    # Trends berechnen
    trends = {
        "IntraDay": (pct_change)  * 1  if pct_change is not None else 0,
        "3T": ((current_price / hist['Close'].iloc[-3]) - 1) * 100 if len(hist) >= 3 else 0,
        "5T": ((current_price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0,
        "1M": ((current_price / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0,
        "6M": ((current_price / hist['Close'].iloc[0]) - 1) * 100
    }
    
    # Fibonacci Level (6 Monate)
    hist_6m = hist.iloc[-126:] # ca. 6 Handelsmonate
    high = hist_6m['High'].max()
    low = hist_6m['Low'].min()
    diff = high - low
    fibs = {
        "0% (High)": high,
        "38.2%": high - 0.382 * diff,
        "50.0%": high - 0.5 * diff,
        "61.8%": high - 0.618 * diff,
        "100% (Low)": low
    }
    return current_price, trends, fibs, hist_6m

def create_chart(ticker, hist, fibs):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Kurs", line=dict(color='#1f77b4', width=2)))
    colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)
    fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# --- HAUPTPROGRAMM ---
st.title("🏛️ Portfolio & Trend Analyzer")

df_port = load_portfolio()

if df_port is not None:
    all_results = []
    total_depot_value = 0.0

    # Datenverarbeitung
    for _, row in df_port.iterrows():
        price, trends, fibs, hist = get_data(row['Symbol'])
        if price:
            total_cost = row['Shares'] * row['CostPerShare']
            current_val = row['Shares'] * price
            total_depot_value += current_val
            
            days_held = (datetime.now() - row['PurchaseDate']).days
            years_held = max(days_held / 365.25, 0.01)
            cagr = ((current_val / total_cost) ** (1 / years_held) - 1) * 100
            
            res = {
                "Symbol": row['Symbol'],
                "Preis": price,
                "Gewinn %": ((current_val/total_cost)-1)*100,
                "Ø Jahr % (CAGR)": cagr
            }
            res.update(trends)
            all_results.append({"data": res, "fibs": fibs, "hist": hist})

    # 1. KPI DASHBOARD
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="custom-info-box"><h3>Anzahl Werte</h3><p>{len(df_port)}</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-info-box"><h3>Depotwert</h3><p>{total_depot_value:,.2f} €</p></div>', unsafe_allow_html=True)
    with c3:
        st.info("**Status:**\n\nKurse sind Live von Yahoo Finance (2 Nachkommastellen)")

    # 2. TABELLE
    st.subheader("Performance & Zeit-Trends")
    summary_df = pd.DataFrame([x['data'] for x in all_results])
    
    # Formatierung definieren
    percent_cols = ['Gewinn %', 'Ø Jahr % (CAGR)', 'IntraDay', '3T', '5T', '1M', '6M']
    format_dict = {col: "{:.2f}%" for col in percent_cols}
    format_dict["Preis"] = "{:.2f} €"

    st.dataframe(
        summary_df.style.format(format_dict)
        .set_properties(**{'background-color': 'white', 'color': 'black'})
        .background_gradient(cmap='RdYlGn', subset=percent_cols),
        use_container_width=True
    )

    # 3. DETAIL ANALYSE
    st.divider()
    selected_ticker = st.selectbox("Aktie für Fibonacci-Check wählen:", summary_df['Symbol'].unique())
    
    if selected_ticker:
        pick = next(item for item in all_results if item['data']['Symbol'] == selected_ticker)
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.plotly_chart(create_chart(selected_ticker, pick['hist'], pick['fibs']), use_container_width=True)
        
        with col_right:
            st.write("**Fibonacci Level (6M):**")
            curr_p = pick['data']['Preis']
            for label, val in pick['fibs'].items():
                diff_pct = abs(curr_p - val) / val * 100
                if diff_pct < 2:
                    st.warning(f"🎯 {label}: {val:.2f} (Nah dran!)")
                else:
                    st.write(f"⚪ {label}: {val:.2f}")