import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import calendar
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

import numpy as np
import pandas as pd

def find_multiple_trends(df, max_trends=4, strong_threshold=0.05):
    """
    Findet den größten Trend und bis zu 3 weitere signifikante Unter-Trends
    innerhalb des übergebenen DataFrames.
    """
    trends = []
    # Wir arbeiten auf einer Kopie der Kurse, um bereits gefundene Bereiche zu "schwächen"
    working_prices = df['Close'].values.copy()
    #dates = df.index
    dates = pd.to_datetime(df.index).tz_localize(None) # Datumsformat erzwingen 
    
    if len(working_prices) < 15:
        return trends

    for i in range(max_trends):
        # Wenn fast keine Kurse mehr übrig sind, abbrechen
        if np.all(np.isnan(working_prices)):
            break
            
        # 1. Finde das aktuelle Maximum und Minimum im (verbleibenden) Datensatz
        abs_max_idx = np.nanargmax(working_prices)
        abs_min_idx = np.nanargmin(working_prices)
        
        first_idx, second_idx = sorted([abs_max_idx, abs_min_idx])
        
        # Sicherheitscheck für Mindestlänge eines Trends (z.B. mindestens 5 Tage)
        if second_idx - first_idx < 5:
            # Bereich ungültig machen, damit wir nicht in eine Endlosschleife laufen
            working_prices[first_idx:second_idx+1] = np.nan
            continue
            
        p_start, p_end = working_prices[first_idx], working_prices[second_idx]
        
        # Wenn durch das vorherige Nullen die Werte korrumpiert sind, skippen
        if np.isnan(p_start) or np.isnan(p_end):
            continue
            
        move_pct = abs(p_end - p_start) / p_start
        
        # Erfüllt der Trend das Mindestkriterium?
        if move_pct >= strong_threshold:
            trends.append({
                "id": f"T{len(trends)+1}",
                "f_start": dates[first_idx],
                "f_end": dates[second_idx],
                "price_start": p_start,
                "price_end": p_end,
                "move_pct": move_pct,
                "type": "Bullish" if p_start < p_end else "Bearish"
            })
            
            # 2. TRICK: Wir "nullen" (NaN) diesen Bereich in unseren Arbeitskursen aus,
            # damit der Algorithmus beim nächsten Durchlauf nach ANDEREN Peaks suchen muss!
            working_prices[first_idx:second_idx+1] = np.nan
        else:
            # Wenn selbst der größte verbleibende Punkt nicht mehr signifikant ist, abbrechen
            working_prices[first_idx:second_idx+1] = np.nan
            
    # Wir sortieren die Trends so, dass der prozentual GRÖSSTE Trend immer auf Platz 1 steht
    trends = sorted(trends, key=lambda x: x["move_pct"], reverse=True)
    
    # IDs nach Sortierung neu vergeben (T1 ist jetzt garantiert der größte)
    for idx, t in enumerate(trends):
        t["id"] = f"T{idx+1}"
        
    return trends

def render_multi_trend_alert_box(trends, ticker):
    """Zeigt den Haupttrend an und steuert den Toggle für den Chart."""
    if not trends:
        return
        
    # T1 ist dank unserer Sortierung immer der mächtigste Trend
    main_trend = trends[0]
    
    trend_type = "Bullish" if main_trend["type"] == "Bullish" else "Bearish"
        
    col_text, col_btn = st.columns([3, 1])
    with col_text:
        if trend_type == "Bullish":
            st.success(
                f"🚀 {ticker} Main Trend **{trend_type}** "
                f"{main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} "
                f"({main_trend['move_pct']*100:.1f}%). "
                f"{len(trends)} trends found."
            )
        else:
            st.info(
                f"🤖 {ticker} Main Trend **{trend_type}** "
                f"{main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} "
                f"({main_trend['move_pct']*100:.1f}%). "
                f"{len(trends)} trends found."
            )

    with col_btn:
        st.markdown("<div style='padding-top: 12px;'></div>", unsafe_allow_html=True)

        # Der Toggle liest seinen Standardwert aus dem Session State
        # Wenn der User klickt, schreibt Streamlit den neuen Wert direkt in die Variable
        inspect_active = st.button(
            f"📈 Visualize Trends", 
            #### key="fibo_trend_inspect", # da wir den state auch ausserhalb setzen !!!!
            help="Show all Fibonacci Trends"
        )
        # Toggle passt Chart-Grenzen (plot_start/end) an den Haupttrend an
        if inspect_active:
            #st.session_state["plot_start"] = main_trend["f_start"].strftime('%Y-%m-%d')
            #st.session_state["plot_end"] = main_trend["f_end"].strftime('%Y-%m-%d')
            st.session_state["fibo_trend_inspect"] = True   
        else:
            # Wenn der Toggle AUS ist, zeigen wir wieder das vom User gewählte Suchfenster
            #st.session_state["plot_start"] = st.session_state.get("sel_start")
            #st.session_state["plot_end"] = st.session_state.get("sel_end")  
            st.session_state["fibo_trend_inspect"] = False              

def find_latest_fibonacci_trend(df, distance=20, prominence=0.05, strong_threshold=0.10):
    """
    strong_threshold: 0.10 bedeutet, der Trend muss mindestens 10% Kursbewegung 
                      vom Start bis zum Ende aufweisen, um als "stark" zu gelten.
    """
    prices = df['Close'].values
    dates = df.index
    
    # 1. Peaks und Troughs suchen
    peaks, _ = find_peaks(prices, distance=distance, prominence=prices.mean() * prominence)
    troughs, _ = find_peaks(-prices, distance=distance, prominence=prices.mean() * prominence)
    extrema = sorted(list(peaks) + list(troughs))
    
    # Standardmäßig gehen wir erst mal von keinem starken Trend aus
    is_strong_trend = False
    
    # 2. Fall: Ein Trend wurde über Extrempunkte gefunden
    if len(extrema) >= 2:
        p1_idx = extrema[-2]
        p2_idx = extrema[-1]
        
        f_start, f_end = dates[p1_idx], dates[p2_idx]
        price_start, price_end = prices[p1_idx], prices[p2_idx]
        
        # Berechne die absolute prozentuale Bewegung des Trends
        trend_move_pct = abs(price_end - price_start) / price_start
        
        # Ein Trend ist stark, wenn er die Prozent-Hürde reißt
        if trend_move_pct >= strong_threshold:
            is_strong_trend = True
            
        return f_start, f_end, price_start, price_end, is_strong_trend
        
    # 3. Fallback: Keine klaren Wendepunkte -> Absolute Extrempunkte nehmen
    else:
        abs_max_idx = np.argmax(prices)
        abs_min_idx = np.argmin(prices)
        first_idx, second_idx = sorted([abs_max_idx, abs_min_idx])
        
        # Auch hier prüfen, ob die Gesamtrange stark genug ist
        trend_move_pct = abs(prices[second_idx] - prices[first_idx]) / prices[first_idx]
        if trend_move_pct >= strong_threshold:
            is_strong_trend = True
            
        return dates[first_idx], dates[second_idx], prices[first_idx], prices[second_idx], is_strong_trend
    

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
    
# Load History data for Ticker - determine Trends and initial Fibonacci-Levels 
def get_ticker_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)

    hist = stock.history(period="3y") # 3 Jahre laden
    if hist.empty: return None, None, None, None, None, None
    
    current_price = hist['Close'].iloc[-1]
    est_target = None
    upside = pct_change = 0
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
    
    return current_price, est_target, upside, pct_change, trends, hist

def create_chart(ticker, hist, fibs, f_trends):
    fig = go.Figure()

    # 1. Zeitzonen-Informationen aus dem Index entfernen (sehr wichtig für Plotly!)
    hist.index = hist.index.tz_localize(None)

    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Kurs", line=dict(color='#1f77b4', width=2)))

    fibo_colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), fibo_colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)
    fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=40, b=20))

    if st.session_state.get("fibo_trend_inspect", True):
        # Farben für die verschiedaenen Trend-Stufen - Haupttrend (T1) 
        # #colors = {1: "#00CC96", 2: "#AB63FA", 3: "#FFA15A", 4: "#19D3F3"}
        trend_colors = {"T1": "#00CC96", "T2": "#AB63FA", "T3": "#FFA15A", "T4": "#19D3F3"}
        
        for t in f_trends:
            # Bestimme die Linienstärke (Haupttrend 1 dick, Untertrends 2-4 dünner)
            width = 4 if t["id"] == 1 else 2
            dash = "solid" if t["id"] == 1 else "dash"
            
            # Füge eine diagonale Trendlinie von Start- bis Endpunkt hinzu
            fig.add_trace(go.Scatter(
                x=[t["f_start"], t["f_end"]], # Sauber auf f_end korrigiert
                y=[t["price_start"], t["price_end"]], 
                mode="lines+markers",
                name=f"Trend {t['id']} ({t['type']})",
                line=dict(color=trend_colors.get(t["id"], "white"), width=width, dash=dash),
                marker=dict(size=6),
                hoverinfo="text",
                hovertext=f"Trend {t['id']}: {t['type']} ({t['move_pct']*100:.1f}%)"
            ))
            
            # Setze die Fibo-Level im Dashboard auf die Werte des HAUPTTRENDS (Trend 1)
            if t["id"] == 1:
                fib_high = max(t["price_start"], t["price_end"])
                fib_low = min(t["price_start"], t["price_end"])
            # ... deine Fibo-Kacheln nutzen im Anschluss diese Werte (fib_high & fib_low) ...

    return fig

def reset_trend_analyse():
    # Setzt die Analyse zurück, sobald der User ein neues Datum wählt
    st.session_state["fibo_trend_analyse"] = False
    # Schaltet auch den Inspektions-Toggle automatisch aus
    st.session_state["fibo_trend_inspect"] = False

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
            price, est_target, upside, pct_change, trends, hist = get_ticker_data(row['Symbol'])
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
                results_temp.append({"data": res, "hist": hist})

        # Jetzt alles in den Session State schreiben
        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_depot_value
        st.session_state.total_depot_cost = total_depot_cost
        st.session_state.total_depot_target = total_depot_target
        st.session_state.ticker_liste = [x['data']['Symbol'] for x in results_temp]

    # Ab hier nutzen wir NUR NOCH den Session State für die Anzeige
    all_results = st.session_state.all_results
    
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

        # Nur diese Spalten erhalten ein "Tag"
        special_headers = {
        'Symbol': '📄 Symbol',
        'Preis': '🌐 Preis',
        'Target': '📈 Target'
        }
        
        # --- FORMATIERUNG samt FEHLER-PRÄVENTION ---
        # Nur Spalten formatieren, die auch wirklich im DF existieren
        actual_format_dict = {k: v for k, v in format_dict.items() if k in summary_df.columns}
        # Sicherstellen, dass keine NaN-Werte in den Prozent-Spalten das Gradient-Rendering stören
        safe_percent_cols = [c for c in percent_cols if c in summary_df.columns]
        summary_df[safe_percent_cols] = summary_df[safe_percent_cols].fillna(0)

        try: # TABLE VIEW  
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
    
    # --- DETAIL ANALYSE MIT STEUERUNG DER ZEITACHSEN ---
    st.divider()
    st.subheader("🔍 Technical Detail-Analysis")
    
    # Session States Detail Ansicht steuern die Zeitachsen für Select, Fib Analyse und Plot separat. Ob Fib Analyse berechnet werden soll
    if "sel_start" not in st.session_state:
        st.session_state["sel_start"] = None # month_options[0]
        st.session_state["plot_start"] = None
        st.session_state["fib_start"] = None

    if "sel_end" not in st.session_state:
        st.session_state["sel_end"] = None 
        st.session_state["plot_end"] = None 
        st.session_state["fib_end"] = None 

    st.session_state["fibo_trend_analyse"] = True  # Toggle für die Trend-Analyse - Berechnung
    st.session_state["fibo_trend_inspect"] = False  # Toggle für die Trend-Inspektion - Plot Fib Bereich
    
    # Ticker-Liste aus den Ergebnissen im Session State holen
    ticker_liste = st.session_state.get('ticker_liste', [])

    # Sicherstellen, dass die Ticker Liste existiert
    if ticker_liste:
        # Session State Index initialisieren
        if 'ticker_index' not in st.session_state:
            st.session_state.ticker_index = 0

        # Funktionen (Callbacks)
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

        # Navigations Select Box and Buttons
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

        # Pro Ticker Detail Anzeige für ausgewählten Wert und Zeitraum
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == ticker_liste[st.session_state.ticker_index]), None) 
        
        if pick:
            hist_full = pick['hist'] # Die kompletten 3 Jahre
            # Index von Zeitzone befreien (sonst Plotly Zeitzonen Konflikte)   
            hist_full.index = hist_full.index.tz_localize(None)

            selected_ticker = pick['data']['Symbol']

            # --- ZEITRAUM STEUERUNG ---
            st.write(f"### 📈 {selected_ticker} - Analyze in time frame")

            # Verfügbare Monate extrahieren
            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]
            idx_end = len(month_options) - 1 # Letzter Monat als Default-Ende
            #idx_start = st.session_state["sel_start"] # selectBox

            #plot_start plot_end im Session State - UI Controls Steuerung
            if "plot_start" not in st.session_state and len(month_options) > 0:
                st.session_state["plot_start"] = month_options[0]   # oldest month
            if "plot_end" not in st.session_state and len(month_options) > 0:
                st.session_state["plot_end"] = month_options[-1]   # youngest month
                        
            # User define Time Window (Monthly only!)
            cols = st.columns([0.5, 1.5, 0.5, 1.5, 1.5], vertical_alignment="center")
            
            cols[0].markdown("**Start**")
            st.session_state["sel_start"] = cols[1].selectbox("Start", options=month_options, index=0, label_visibility="collapsed")

            cols[2].markdown("**End**")
            st.session_state["sel_end"] = cols[3].selectbox("End", options=month_options, index=idx_end, label_visibility="collapsed")

            if cols[4].button(f"🔍 Analyse Range", help="Analyse Fibonacci levels on the selected time range."):
                st.session_state["fibo_trend_analyse"] = True # nur ändern wenn Range geändert wird, nicht bei jedem UI Update
                st.session_state["fib_start"] = st.session_state["sel_start"]
                st.session_state["fib_end"] = st.session_state["sel_end"]

            # plotten bis Monatsende 
            st.session_state["plot_start"] = st.session_state["sel_start"]
            st.session_state["plot_end"] = pd.to_datetime(st.session_state["sel_end"]) + pd.offsets.MonthEnd(0) 

            # --- DATEN FILTERN & FIBONACCI BERECHNEN ---
            
            # --- FIBO TREND-ANALYSE in FILTERED / HIST_FULL ---
            if st.session_state.get("fibo_trend_analyse", True):
                fib_mask = (hist_full.index >= pd.to_datetime(st.session_state["fib_start"])) & (hist_full.index <= pd.to_datetime(st.session_state["fib_end"]))
                fib_hist = hist_full.loc[fib_mask]
    
                fib_trends = find_multiple_trends(fib_hist, max_trends=4, strong_threshold=0.05)
                
                # Damit wir nicht bei jedem UI-Update neu berechnen
                st.session_state["fibo_trend_analyse"] = False 

                fib_trend_type = fib_trends[0]["type"] if len(fib_trends) > 0 else None            
                fib_strong_trend = fib_trends[0]["move_pct"] >= 0.05 if len(fib_trends) > 0 else False
                fib_start = fib_trends[0]["f_start"] if len(fib_trends) > 0 else None
                fib_end = fib_trends[0]["f_end"] if len(fib_trends) > 0 else None

            cols = st.columns([3, 1],   vertical_alignment="center")

            render_multi_trend_alert_box(fib_trends, selected_ticker)  # Zeigt den Haupttrend + Toggle für die Trend-Inspektion
                                       
            plot_mask = (hist_full.index >= pd.to_datetime(st.session_state["plot_start"])) & (hist_full.index <= pd.to_datetime(st.session_state["plot_end"]))
            plot_hist = hist_full.loc[plot_mask]

            # XXXXX Filtern der Daten auf den gewählten Bereich            
            h = 0 if plot_hist.empty else plot_hist['High'].max()
            l = 0 if plot_hist.empty else plot_hist['Low'].min()
            d = h - l
            
            dynamic_fibs = {
                "0% (High)": h,
                "38.2% Retracement": h - 0.382 * d,
                "50.0% Center Line": h - 0.5 * d,
                "61.8% Golden Pocket": h - 0.618 * d,
                "100% (Low Base)": l
            }

            # --- AUSGABE ---
            if st.session_state["fibo_trend_inspect"] == True:
            # Der Chart auf voller Breite
                st.plotly_chart(
                    create_chart(selected_ticker, plot_hist, dynamic_fibs, fib_trends), 
                    use_container_width=True
                )
            else:
            # Der Chart neben KPI Metrics
                chart_col, sidebar_col = st.columns([4, 1])
                with chart_col:
                    st.plotly_chart(
                        create_chart(selected_ticker, plot_hist, dynamic_fibs, fib_trends), 
                        use_container_width=True
                    )            

                with sidebar_col: # Key Metric oder fibo Trend Analyse - Platzbedarf 
                    st.write(f"### {selected_ticker} - Key Metrics")
                    curr_p = pick['data']['🌐 Price']
                    
                    # KPI Metric (Target Price)
                    try:
                        s_obj = yf.Ticker(selected_ticker)
                        target = s_obj.info.get('targetMeanPrice')
                        if target:
                            up_val = ((target / curr_p) - 1) * 100
                            if up_val > 0:
                                st.markdown( # Positiv: Grüner Pfeil nach oben + "Upside"
                                    f"""
                                    <div style="background-color: #e6f4ea; color: #137333; padding: 4px 8px; border-radius: 4px; display: inline-block; font-weight: bold;">
                                        1Y Target Estimate: {target:.2f} $<br>
                                        ↑ {up_val:.1f}% Upside from {curr_p:.2f} $ <br>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )
                            else:       
                                st.markdown( # Negativ: Roter Pfeil nach unten + "Downside"
                                    f"""
                                    <div style="background-color: #fce8e6; color: #c5221f; padding: 4px 8px; border-radius: 4px; display: inline-block; font-weight: bold;">
                                        1Y Target Estimate: {target:.2f} $<br>
                                        ↓ {abs(up_val):.1f}% Downside from {curr_p:.2f} $ <br>
                                    </div>
                                    """, 
                                    unsafe_allow_html=True
                                )   
                    except:
                        st.caption("Analyst-Target not available")

                    # Dynamische Fibonacci Liste
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.subheader(f"Fibonacci Levels")
            
                    # Fibonacci-Level basierend auf dynamischen Werten
                    st.caption(f"Calculated from {st.session_state['sel_start']} to {st.session_state['sel_end']}")
                    with st.container():
                        #st.write(f"**Fibonacci (from {sel_start} to {sel_end})**")
                        for label, val in dynamic_fibs.items():
                            # Optische Markierung, wenn der Kurs nah an einem Level ist
                            prox = abs(curr_p - val) / val * 100
                            if prox < 1.5:
                                prefix= "🎯"
                            else:
                                prefix = "⚪"
                            st.write(f"{prefix} **{label}: {val:.2f}**")
        else:
            st.error("No data available for this time frame.")      