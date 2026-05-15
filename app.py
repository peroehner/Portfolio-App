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

def get_ticker_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)

    hist = stock.history(period="3y") # 3 Jahre laden
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
    
    # Init Fibonacci Level (12 Monate)
    hist_12m = hist.iloc[-21*12:] # ca. 12 Handelsmonate
    high = hist_12m['High'].max()
    low = hist_12m['Low'].min()
    diff = high - low
    fibs = {
        "0% (High)": high,
        "38.2%": high - 0.382 * diff,
        "50.0%": high - 0.5 * diff,
        "61.8%": high - 0.618 * diff,
        "100% (Low)": low
    }
    return current_price, tGM, upside, pct_change, trends, fibs, hist

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

df_port = load_portfolio()
if df_port is not None:
    # WICHTIG: Prüfen, ob Daten schon da sind, sonst laden
    if 'all_results' not in st.session_state:
        results_temp = []
        total_val_temp = 0.0

        for _, row in df_port.iterrows():
            price, tGM, upside, pct_change, trends, fibs, hist = get_ticker_data(row['Symbol'])
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

    # Formattierung nach Sicherstellung vorhandener Daten im Session State
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

    # 1. Ticker-Liste aus den Ergebnissen im Session State holen
    ticker_liste = st.session_state.get('ticker_liste', [])
    #selected_ticker = None  # Standardmäßig auf None setzen

    # Sicherstellen, dass die Liste existiert
    if ticker_liste:
        # 2. Session State Index initialisieren
        if 'ticker_index' not in st.session_state:
            st.session_state.ticker_index = 0

        # 3. Funktionen (Callbacks)
        def move_next():
            st.session_state.ticker_index = (st.session_state.ticker_index + 1) % len(ticker_liste)
            st.session_state.sb_selector = ticker_liste[st.session_state.ticker_index]  # Synchronisieren mit Selectbox

        def move_prev():
            st.session_state.ticker_index = (st.session_state.ticker_index - 1) % len(ticker_liste)
            st.session_state.sb_selector = ticker_liste[st.session_state.ticker_index]  # Synchronisieren mit Selectbox
        
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
            st.selectbox(
                "Symbol",
                options=ticker_liste,
                index=st.session_state.ticker_index,
                key="sb_selector",
                on_change=sync_index,
                label_visibility="collapsed"
            )

        # 5. Detail Anzeige für ausgewählten Wert und Zeitraum
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == ticker_liste[st.session_state.ticker_index]), None) 
        
        if pick:
            hist_full = pick['hist'] # Die kompletten 3 Jahre
            selected_ticker = pick['data']['Symbol']

            # --- ZEITRAUM STEUERUNG ---
            st.write("### 📅 Analyse-Zeitraum ")
            
            # Verfügbare Monate extrahieren
            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]
            
            # Defaults berechnen (Ende = Jetzt, Start = vor 12 Monaten)
            idx_end = len(month_options) - 1
            idx_start = max(0, idx_end - 12)
            
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                sel_start = st.selectbox("Start-Monat", options=month_options, index=idx_start)
            with col_date2:
                sel_end = st.selectbox("End-Monat", options=month_options, index=idx_end)
            
            # --- DATEN FILTERN & FIBONACCI BERECHNEN ---
            # Filtern der Daten auf den gewählten Bereich
            mask = (hist_full.index >= sel_start) & (hist_full.index <= sel_end)
            hist_filtered = hist_full.loc[mask]
            
            if not hist_filtered.empty:
                h = hist_filtered['High'].max()
                l = hist_filtered['Low'].min()
                d = h - l
                
                dynamic_fibs = {
                    "0% (High)": h,
                    "38.2%": h - 0.382 * d,
                    "50.0%": h - 0.5 * d,
                    "61.8%": h - 0.618 * d,
                    "100% (Low)": l
                }

                # --- AUSGABE IN DEN ZWEI SPALTEN ---
                col_left, col_right = st.columns([2, 1])
                
                with col_left:
                    # Der Chart nutzt jetzt die gefilterten Daten und die neuen Fibs
                    st.plotly_chart(create_chart(selected_ticker, hist_filtered, dynamic_fibs), use_container_width=True)
                
                with col_right:
                    st.write(f"### Details: {selected_ticker}")
                    curr_p = pick['data']['Preis']
                    
                    # KPI Metric (Target Price)
                    try:
                        s_obj = yf.Ticker(selected_ticker)
                        target = s_obj.info.get('targetMeanPrice')
                        if target:
                            up_val = ((target / curr_p) - 1) * 100
                            st.metric("1Y Target Estimate", f"{target:.2f} €", f"{up_val:.1f}% Upside")
                    except:
                        st.caption("Analysten-Target nicht abrufbar")

                    # Dynamische Fibonacci Liste
                    st.write(f"**Fibonacci (Zeitraum: {sel_start} bis {sel_end})**")
                    for label, val in dynamic_fibs.items():
                        # Optische Markierung, wenn der Kurs nah an einem Level ist
                        prox = abs(curr_p - val) / val * 100
                        if prox < 1.5:
                            st.warning(f"🎯 **{label}: {val:.2f}**")
                        else:
                            st.write(f"⚪ {label}: {val:.2f}")
            else:
                st.error("Keine Daten für diesen Zeitraum verfügbar.")      