import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# --- KONFIGURATION & THEME ---
st.set_page_config(
        page_title="Portfolio Architektur Pro",
        page_icon="myPeroLogo.png",
        layout="wide"
        )

st.markdown(
    """
    <head>
        <link rel="apple-touch-icon" sizes="180x180" href="myPeroLogo.png">
        <link rel="apple-touch-startup-image" href="myPeroLogo.png">
    </head>
    """,
    unsafe_allow_html=True
)

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
        st.error(f"Datei 'Sample-Portfolio.csv' not found or corrupt: {e}")
        return None

def get_exchange_rate():
    try:
        # Ticker für Euro/Dollar
        fx = yf.Ticker("EURUSD=X")
        rate = 1 / fx.history(period="1d")['Close'].iloc[-1]
        return rate
    except:
        # Fallback, falls die API hakt (ungefährer Wert)
        return 0.92
    
# Hauptfunktion zum Abrufen der Ticker-Daten, Trends und initiale Fibonacci-Level
def get_ticker_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)

    hist = stock.history(period="3y") # 3 Jahre laden
    if hist.empty: return None, None, None, None, None, None, None
    
    current_price = hist['Close'].iloc[-1]
    
    # Wir nutzen einen try-except Block, damit die App nicht crashed, wenn .info leer ist    
    est_target = None
    upside = 0
    pct_change = 0
    try:
        info = stock.info
        if info:
            pct_change = info.get('regularMarketChangePercent')
            est_target = info.get('targetMeanPrice')
            if est_target:
                upside = ((est_target / current_price) - 1) * 100
    except Exception:
        pass
    
    # Trends berechnen
    trends = {
        "1D": (pct_change)  * 1  if pct_change is not None else 0,
        "3D": ((current_price / hist['Close'].iloc[-3]) - 1) * 100 if len(hist) >= 3 else 0,
        "5D": ((current_price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0,
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
    return current_price, est_target, upside, pct_change, trends, fibs, hist

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
        total_depot_value = 0.0
        total_depot_cost = 0.0
        total_depot_target = 0.0    

        for _, row in df_port.iterrows(): # Portfolio zeilenweise durchlaufen
            price, est_target, upside, pct_change, trends, fibs, hist = get_ticker_data(row['Symbol'])
            if price:
                # Ermittluung der Portfolio Werte und Currency Handling
                cost_per_share = row['AvgCost']
                target = row['TargetPrice']
                if row['Currency'] == 'EUR': 
                    # Ggf. Euro in Dollar umrechnen
                    rate = get_exchange_rate()
                    cost_per_share /= rate
                    target /= rate
                    
                current_val = row['Shares'] * price
                current_cost = row['Shares'] * cost_per_share
                current_target = row['Shares'] * target

                # Deopt Summen für Gesamtübersicht 
                total_depot_value  += current_val
                total_depot_cost   += current_cost
                total_depot_target += current_target

                # Deine Berechnungen (Target, CAGR etc.)
                diff_target_abs = abs(target - price)
                diff_target_pct = abs(target - price) / price if price != 0 else 0
                days_held = (datetime.now() - row['PurchaseDate']).days
                years_held = max(days_held / 365.25, 0.01)
                cagr = ((current_val / current_cost) ** (1 / years_held) - 1) * 100
                
                res = { # NB - defines columns order in the final table - left to right
                    "Symbol": row['Symbol'], "🌐 Price": price, "Change %": pct_change, 
                    "Est Target": est_target, "Upside %": upside, 
                    "📈 Target": target,
                    "Target %": diff_target_pct * 100, "Target $": diff_target_abs,
                    "📈 Total %": ((current_val/current_cost)-1)*100, "Ø CAGR": cagr
                }
                res.update(trends)
                results_temp.append({"data": res, "fibs": fibs, "hist": hist})

        # Jetzt alles in den Session State schreiben
        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_depot_value
        st.session_state.total_depot_cost = total_depot_cost
        st.session_state.total_depot_target = total_depot_target
        st.session_state.ticker_liste = [x['data']['Symbol'] for x in results_temp]

    # Ab hier nutzen wir NUR NOCH den Session State für die Anzeige
    all_results = st.session_state.all_results
    total_depot_value = st.session_state.total_depot_value

    # 1. KPI DASHBOARD
    st.subheader("Depot Metrics & Status")
    st.caption(f"✨ **{len(df_port):,} Symbols** in Portfolio • Source: Live from Yahoo Finance •")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="custom-info-box"><h3>Actual</h3><p>{st.session_state.total_depot_value:,.0f} $</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-info-box"><h3>Cost</h3><p>{st.session_state.total_depot_cost:,.0f} $</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="custom-info-box"><h3>Target</h3><p>{st.session_state.total_depot_target:,.0f} $</p></div>', unsafe_allow_html=True)        

    # 2. TABELLE
    st.subheader("Performance & Trends")
 
    # Formattierung nach Sicherstellung vorhandener Daten im Session State
    if 'all_results' in st.session_state and len(st.session_state.all_results) > 0:
        summary_df = pd.DataFrame([x['data'] for x in st.session_state.all_results])
        
        # Formatierung definieren
        percent_cols = ['📈 Total %', 'Change %', 'Upside %', 'Ø CAGR',"Target %", '1D', '3D', '5D', '1M', '6M']
        format_dict = {col: "{:.2f}%" for col in percent_cols}
        format_dict["📈 Target"] = "{:.0f} $"
        format_dict["Target $"] = "{:.0f} $"
        format_dict["Est Target"] = "{:.0f} $"
        format_dict["🌐 Price"] = "{:.1f} $"
        # WAS: summary_df.style.format(format_dict)
                       # Mapping der Spaltennamen

        # Nur diese Spalten erhalten ein "Tag"
        special_headers = {
        'Symbol': '📄 Symbol',
        'Preis': '🌐 Preis',
        'Target': '📈 Target'
        }
        # .rename() ändert nur die Treffer im Dictionary
        # styled_df = summary_df.rename(columns=special_headers)
        # summary_df = st.dataframe(styled_df)

        # --- FORMATIERUNG samt FEHLER-PRÄVENTION ---
        # 1. Nur Spalten formatieren, die auch wirklich im DF existieren
        actual_format_dict = {k: v for k, v in format_dict.items() if k in summary_df.columns}
        
        # 2. Sicherstellen, dass keine NaN-Werte in den Prozent-Spalten das Gradient-Rendering stören
        safe_percent_cols = [c for c in percent_cols if c in summary_df.columns]
        summary_df[safe_percent_cols] = summary_df[safe_percent_cols].fillna(0)

        try:
            # Versuche die schicke Formatierung
            st.dataframe(
                summary_df.style.format(actual_format_dict, na_rep='-')
                .set_properties(**{'background-color': 'white', 'color': 'black'})
                .background_gradient(cmap='RdYlGn', subset=safe_percent_cols),
                use_container_width=True
            )
        except Exception as e:
            # BACKUP: Falls der Styler im Deployment immer noch zickt (z.B. wegen Bibliotheks-Konflikten)
            # zeigen wir die Tabelle ohne Schnickschnack an, damit die App nicht crashed.
            st.dataframe(summary_df, use_container_width=True)
            st.caption(f"Hint: Table-Styling deactivated ({e})")   
    else:
        st.warning("No data to analyze in table available.") 
        summary_df = pd.DataFrame([x['data'] for x in all_results])         
    
    # --- DETAIL ANALYSE MIT STEUERUNG ---
    st.divider()
    st.subheader("🔍 Technical Detail-Analysis")

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
            st.button("⬅️ Prev", on_click=move_prev, key="nav_prev", use_container_width=True)

        with col_next:
            st.button("Next ➡️", on_click=move_next, key="nav_next", use_container_width=True)

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
            st.write("### 📅 Analyze in time frame")
            
            # Verfügbare Monate extrahieren
            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]
            
            # Defaults berechnen (Ende = Jetzt, Start = vor 12 Monaten)
            idx_end = len(month_options) - 1
            idx_start = max(0, idx_end - 12)
            
            cols = st.columns([0.5, 1.5, 0.5, 1.5], vertical_alignment="center")

            cols[0].markdown("**Start**")
            sel_start = cols[1].selectbox("Start", options=month_options, index=0, label_visibility="collapsed")
            cols[2].markdown("**End**")
            sel_end = cols[3].selectbox("End", options=month_options, index=idx_end, label_visibility="collapsed")  
           
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
                    curr_p = pick['data']['🌐 Price']
                    
                    # KPI Metric (Target Price)
                    try:
                        s_obj = yf.Ticker(selected_ticker)
                        target = s_obj.info.get('targetMeanPrice')
                        if target:
                            up_val = ((target / curr_p) - 1) * 100
                            st.metric("1Y Target Estimate", f"{target:.2f} $", f"From {curr_p:.1f}$ {up_val:.1f}% Upside")
                    except:
                        st.caption("Analyst-Target not available")

                    # Dynamische Fibonacci Liste
                    st.write(f"**Fibonacci (from {sel_start} to {sel_end})**")
                    for label, val in dynamic_fibs.items():
                        # Optische Markierung, wenn der Kurs nah an einem Level ist
                        prox = abs(curr_p - val) / val * 100
                        if prox < 1.5:
                            st.warning(f"🎯 **{label}: {val:.2f}**")
                        else:
                            st.write(f"⚪ {label}: {val:.2f}")
            else:
                st.error("No data available for this time frame.")      