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
    hist = stock.history(period="12mo") # Puffer für 12M Trends
    if hist.empty: return None, None, None, None
    
    current_price = hist['Close'].iloc[-1]
    pct_change = stock.info.get('regularMarketChangePercent')
    # print(f"Veränderung: {pct_change}%")

    # Analysten-Daten abrufen
    tGM = stock.info.get('targetMeanPrice')
    upside = ((tGM / current_price ) - 1) * 100
    
    # Trends berechnen
    trends = {
        "IntraDay": (pct_change)  * 1  if pct_change is not None else 0,
        "3T": ((current_price / hist['Close'].iloc[-3]) - 1) * 100 if len(hist) >= 3 else 0,
        "5T": ((current_price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0,
        "1M": ((current_price / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0,
        "6M": ((current_price / hist['Close'].iloc[0]) - 1) * 100
    }
    
    # Fibonacci Level (6 Monate)
    hist_6m = hist.iloc[-196:] # ca. 6 Handelsmonate
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
    return current_price, tGM, upside, pct_change, trends, fibs, hist_6m

def create_chart(ticker, hist, fibs):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Kurs", line=dict(color='#1f77b4', width=2)))
    colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)
    fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# --- HAUPTPROGRAMM ---
st.title("🏛️ Pero Portfolio & Trend Analyzer")

selected_ticker = None  # Standardmäßig auf None setzen

df_port = load_portfolio()
if df_port is not None:
    # WICHTIG: Prüfen, ob Daten schon da sind, sonst laden
    if 'all_results' not in st.session_state:
        results_temp = []
        total_val_temp = 0.0

        for _, row in df_port.iterrows():
            price, tGM, upside, pct_change, trends, fibs, hist = get_data(row['Symbol'])
            if price:
                total_cost = row['Shares'] * row['CostPerShare']
                current_val = row['Shares'] * price
                total_val_temp += current_val
                
                # Deine Berechnungen (Target, CAGR etc.)
                pct = row['TargetPrice']
                diff_abs_pct = abs(pct - price)
                diff_per_pct = abs(pct - price) / price if price != 0 else 0
                days_held = (datetime.now() - row['PurchaseDate']).days
                years_held = max(days_held / 365.25, 0.01)
                cagr = ((current_val / total_cost) ** (1 / years_held) - 1) * 100
                
                res = {
                    "Symbol": row['Symbol'], "Preis": price, "Est Target": tGM,
                    "Upside %": upside, "Change %": pct_change, "Target": pct,
                    "D Target %": diff_per_pct * 100, "D Target": diff_abs_pct,
                    "Gewinn %": ((current_val/total_cost)-1)*100, "Ø Jahr % (CAGR)": cagr
                }
                res.update(trends)
                results_temp.append({"data": res, "fibs": fibs, "hist": hist})

        # Jetzt alles in den Session State schreiben
        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_val_temp
        st.session_state.ticker_liste = [x['data']['Symbol'] for x in results_temp]

    # Ab hier nutzen wir NUR NOCH den Session State für die Anzeige
    all_results = st.session_state.all_results
    total_depot_value = st.session_state.total_depot_value

    # Datenverarbeitung
    for _, row in df_port.iterrows():
        price, tGM, upside, pct_change, trends, fibs, hist = get_data(row['Symbol'])
        if price:
            total_cost = row['Shares'] * row['CostPerShare']
            current_val = row['Shares'] * price
            total_depot_value += current_val
            
            pct = row['TargetPrice']
            diff_abs_pct = abs(pct - price)
            diff_per_pct = abs(pct - price) / price if price != 0 else 0


            days_held = (datetime.now() - row['PurchaseDate']).days
            years_held = max(days_held / 365.25, 0.01)
            cagr = ((current_val / total_cost) ** (1 / years_held) - 1) * 100
            
            res = {
                "Symbol": row['Symbol'],
                "Preis": price,
                "Est Target": tGM,
                "Upside %": upside,
                "Change %": pct_change,
                "Target": pct,
                "D Target %": diff_per_pct * 100,
                "D Target": diff_abs_pct,
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
        st.info("**Status:**\n\nKurse Live von Yahoo Finance")

    # 2. TABELLE
    st.subheader("Performance & Zeit-Trends")

    # Sicherstellen, dass Daten im Session State vorhanden sind
    if 'all_results' in st.session_state and st.session_state.all_results:
        summary_df = pd.DataFrame([x['data'] for x in st.session_state.all_results])
        
        # Formatierung definieren
        percent_cols = ['Gewinn %', 'Change %', 'Upside %', 'Ø Jahr % (CAGR)',"D Target %", 'IntraDay', '3T', '5T', '1M', '6M']
        format_dict = {col: "{:.2f}%" for col in percent_cols}
        format_dict["D Target"] = "{:.2f} €"
        format_dict["Preis"] = "{:.2f} €"
        format_dict["Est Target"] = "{:.2f} €"

        st.dataframe(
            summary_df.style.format(format_dict)
            .set_properties(**{'background-color': 'white', 'color': 'black'})
            .background_gradient(cmap='RdYlGn', subset=percent_cols),
            use_container_width=True
        )    
    else:
        st.warning("Keine Daten zur Anzeige in der Tabelle verfügbar.") 
        summary_df = pd.DataFrame([x['data'] for x in all_results])         
    
    # --- DETAIL ANALYSE MIT STEUERUNG ---
    st.divider()
    st.subheader("🔍 Technische Detail-Analyse")

    # 1. Ticker-Liste aus den Ergebnissen ziehen (Wir nutzen all_results aus dem Session State)
    ticker_liste = st.session_state.get('ticker_liste', [])

    # Sicherstellen, dass die Liste existiert
    if ticker_liste:
        # 2. Session State Index initialisieren
        if 'ticker_index' not in st.session_state:
            st.session_state.ticker_index = 0

        # 3. Funktionen (Callbacks)
        def move_next():
            st.session_state.ticker_index = (st.session_state.ticker_index + 1) % len(ticker_liste)

        def move_prev():
            st.session_state.ticker_index = (st.session_state.ticker_index - 1) % len(ticker_liste)
        
        def sync_index():
            # Wenn der User die Liste nutzt, aktualisieren wir den Index
            val = st.session_state.sb_selector
            st.session_state.ticker_index = ticker_liste.index(val)

        # 4. Navigations-UI
        col_prev, col_select, col_next = st.columns([1, 3, 1])
        
        with col_prev:
            st.button("⬅️ Zurück", on_click=move_prev, key="nav_prev", use_container_width=True)

        with col_next:
            st.button("Weiter ➡️", on_click=move_next, key="nav_next", use_container_width=True)

        with col_select:
            # WICHTIG: Die Selectbox definiert hier den selected_ticker
            selected_ticker = st.selectbox(
                "Symbol",
                options=ticker_liste,
                index=st.session_state.ticker_index, # Gesteuert durch Buttons
                key="sb_selector",
                on_change=sync_index,
                label_visibility="collapsed"
            )

        # KRITISCH: Wir erzwingen, dass selected_ticker immer zum Index passt
        # Falls der Button geklickt wurde, nehmen wir den Wert direkt aus der Liste
        selected_ticker = ticker_liste[st.session_state.ticker_index]

        # 5. Anzeige-Logik (Eingerückt innerhalb von "if df_port is not None")
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == selected_ticker), None) 
        
        if pick:
            col_left, col_right = st.columns([2, 1])
            
            st.write(f"### {selected_ticker}")

            with col_left:
                st.plotly_chart(create_chart(selected_ticker, pick['hist'], pick['fibs']), use_container_width=True)
            
            with col_right:
                st.write(f"### {selected_ticker}")
                curr_p = pick['data']['Preis']
                
                try:
                    s_obj = yf.Ticker(selected_ticker)
                    target = s_obj.info.get('targetMeanPrice')
                    if target:
                        upside_val = ((target / curr_p) - 1) * 100
                        st.metric("1Y Target Estimate", f"{target:.2f} €", f"{upside_val:.1f}% Upside")
                except:
                    st.caption("Kein Analysten-Target verfügbar")

                st.write("**Fibonacci Level (6M):**")
                for label, val in pick['fibs'].items():
                    diff_pct = abs(curr_p - val) / val * 100
                    if diff_pct < 2:
                        st.warning(f"🎯 {label}: {val:.2f}")
                    else:
                        st.write(f"⚪ {label}: {val:.2f}")