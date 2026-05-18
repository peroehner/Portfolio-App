import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import calendar
from datetime import datetime
import numpy as np
from scipy.signal import find_peaks
import sys
import os

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

# Zentrales CSS für Lesbarkeit, Box-Design und kompakten Uploader
st.markdown("""
    <style>
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
        color: #000000;
    }
    [data-testid="stDataFrame"] td {
        color: black !important;
    }
    /* Macht den File Uploader kompakt für die Inline-Anzeige im Header */
    [data-testid="stFileUploader"] {
        padding-bottom: 0px;
    }
    [data-testid="stFileUploader"] section {
        padding: 0px 10px;
        min-height: 38px;
    }
    </style>
    """, unsafe_allow_html=True)


# --- PARSE COMMAND LINE ARGUMENTS ---
def get_cli_filename():
    """Extrahiert den Dateinamen, falls via '-f <filename>' im Terminal übergeben."""
    try:
        args = sys.argv
        if "-f" in args:
            idx = args.index("-f")
            if idx + 1 < len(args):
                potential_file = args[idx + 1]
                if os.path.exists(potential_file):
                    return potential_file
    except:
        pass
    return None


# --- KERN-ALGORITHMEN ---

def find_multiple_trends(df, max_trends=4, strong_threshold=0.05):
    """Findet den größten Trend und bis zu 3 weitere signifikante Unter-Trends."""
    trends = []
    if df is None or df.empty or 'Close' not in df.columns:
        return trends
        
    working_prices = df['Close'].values.copy()
    dates = pd.to_datetime(df.index).tz_localize(None)
    
    if len(working_prices) < 15:
        return trends

    for i in range(max_trends):
        if np.all(np.isnan(working_prices)):
            break
            
        abs_max_idx = np.nanargmax(working_prices)
        abs_min_idx = np.nanargmin(working_prices)
        
        first_idx, second_idx = sorted([abs_max_idx, abs_min_idx])
        
        if second_idx - first_idx < 5:
            working_prices[first_idx:second_idx+1] = np.nan
            continue
            
        p_start, p_end = working_prices[first_idx], working_prices[second_idx]
        
        if np.isnan(p_start) or np.isnan(p_end):
            continue
            
        move_pct = abs(p_end - p_start) / p_start
        
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
            working_prices[first_idx:second_idx+1] = np.nan
        else:
            working_prices[first_idx:second_idx+1] = np.nan
            
    trends = sorted(trends, key=lambda x: x["move_pct"], reverse=True)
    for idx, t in enumerate(trends):
        t["id"] = f"T{idx+1}"
        
    return trends


def render_multi_trend_alert_box(trends, ticker):
    """Zeigt den Haupttrend an und steuert den Toggle für den Chart."""
    if not trends:
        return
        
    main_trend = trends[0]
    trend_type = main_trend["type"]
        
    col_text, col_btn = st.columns([3, 1])
    with col_text:
        if trend_type == "Bullish":
            st.success(
                f"🚀 {ticker} Main Trend **{trend_type}** "
                f"{main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} "
                f"({main_trend['move_pct']*100:.1f}%). {len(trends)} trends found."
            )
        else:
            st.info(
                f"🤖 {ticker} Main Trend **{trend_type}** "
                f"{main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} "
                f"({main_trend['move_pct']*100:.1f}%). {len(trends)} trends found."
            )

    with col_btn:
        st.markdown("<div style='padding-top: 12px;'></div>", unsafe_allow_html=True)
        inspect_active = st.button(f"📈 Visualize Trends", help="Show all Fibonacci Trends")
        if inspect_active:
            st.session_state["fibo_trend_inspect"] = True   
        else:
            st.session_state["fibo_trend_inspect"] = False              


# --- DATENBESCHAFFUNG ---

def load_portfolio(uploaded_file):
    """Lädt das Portfolio aus dem Uploader, CLI-Argumenten oder lokalen Dateien."""
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file, sep=';')
            df['PurchaseDate'] = pd.to_datetime(df['PurchaseDate'])
            return df, uploaded_file.name

        cli_file = get_cli_filename()
        if cli_file is not None:
            df = pd.read_csv(cli_file, sep=';')
            df['PurchaseDate'] = pd.to_datetime(df['PurchaseDate'])
            return df, cli_file

        try:
            df = pd.read_csv("mySamplePortfolio.csv", sep=';')
            filename = "mySamplePortfolio.csv"
        except Exception as e:
            st.error(f"Datei 'mySamplePortfolio.csv' nicht gefunden: {e}")
            return None, "Kein Portfolio geladen"
                
        df['PurchaseDate'] = pd.to_datetime(df['PurchaseDate'])
        return df, filename
    except Exception as e:
        st.error(f"Fehler beim Laden des Portfolios: {e}")
        return None, "Fehler beim Laden"


def get_exchange_rate():
    try:
        fx = yf.Ticker("EURUSD=X")
        return 1 / fx.history(period="1d")['Close'].iloc[-1]
    except:
        return 0.92


@st.cache_data(ttl=3600)
def get_ticker_metadata(ticker_symbol):
    """Holt Metadaten (KPIs) separat und stark gecached, um API-Anfragen klein zu halten."""
    stock = yf.Ticker(ticker_symbol)
    est_target = None
    pct_change = 0
    try:
        info = stock.info
        if info:
            pct_change = info.get('regularMarketChangePercent', 0)
            est_target = info.get('targetMeanPrice')
    except:
        pass
    return est_target, pct_change


# --- CHARTING ---

def create_chart(ticker, hist, fibs, f_trends):
    fig = go.Figure()
    if hist is None or hist.empty:
        return fig

    hist.index = hist.index.tz_localize(None)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Kurs", line=dict(color='#1f77b4', width=2)))

    fibo_colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), fibo_colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)
        
    fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=40, b=20))

    if st.session_state.get("fibo_trend_inspect", False) and f_trends:
        trend_colors = {"T1": "#00CC96", "T2": "#AB63FA", "T3": "#FFA15A", "T4": "#19D3F3"}
        for t in f_trends:
            width = 4 if t["id"] == "T1" else 2
            dash = "solid" if t["id"] == "T1" else "dash"
            
            fig.add_trace(go.Scatter(
                x=[t["f_start"], t["f_end"]], 
                y=[t["price_start"], t["price_end"]], 
                mode="lines+markers",
                name=f"Trend {t['id']} ({t['type']})",
                line=dict(color=trend_colors.get(t["id"], "#7f7f7f"), width=width, dash=dash),
                marker=dict(size=6, color=trend_colors.get(t["id"], "#7f7f7f")),
                hoverinfo="text",
                hovertext=f"Trend {t['id']}: {t['type']} ({t['move_pct']*100:.1f}%)"
            ))
    return fig


# --- HAUPTPROGRAMM INTERFACE ---

st.title("🏛️ Pero Portfolio & Trend Analyzer")

# State-Tracking für die Identität des Uploader-Widgets
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# 1. FILE MANAGER PART & WORKSPACE HEADER (Wiederhergestellt!)
hdr_col1, hdr_col2, hdr_col3 = st.columns([2.0, 2.5, 0.5], vertical_alignment="center")

temp_file = st.session_state.get(f"portfolio_upload_{st.session_state.uploader_key}")
df_port, current_portfolio_name = load_portfolio(temp_file)

with hdr_col1:
    st.subheader(f"💼 Workspace: {current_portfolio_name}")

with hdr_col2:
    user_file = st.file_uploader(
        "Upload custom portfolio CSV (';')", 
        type=["csv"], 
        label_visibility="collapsed",
        key=f"portfolio_upload_{st.session_state.uploader_key}"
    )

with hdr_col3:
    is_cli_active = get_cli_filename() is not None
    if temp_file is not None or is_cli_active:
        if st.button("❌", help="Reset auf Standard-Portfolio"):
            st.session_state.uploader_key += 1
            if 'all_results' in st.session_state:
                del st.session_state['all_results']
            st.rerun()

st.markdown("---")

if df_port is not None:
    # WICHTIG: Cache auf Basis des aktuellen Portfolionamens prüfen
    if 'current_loaded_name' not in st.session_state or st.session_state.current_loaded_name != current_portfolio_name:
        st.session_state.current_loaded_name = current_portfolio_name
        results_temp = []
        total_depot_value = 0.0
        total_depot_cost = 0.0
        total_depot_target = 0.0    

        # --- REPARIERTER BULK DOWNLOAD (Echte Beschleunigung) ---
        ticker_liste_all = df_port['Symbol'].unique().tolist()
        
        with st.spinner("Hole alle Live-Marktdaten parallel von Yahoo Finance..."):
            try:
                # Schneller, standardisierter Download aller Ticker nebeneinander
                bulk_data = yf.download(ticker_liste_all, period="3y", progress=False)
                # Extrahiere nur die Close-Preise (High/Low optional für Fibo-Filterung)
                bulk_close = bulk_data['Close'] if len(ticker_liste_all) > 1 else pd.DataFrame(bulk_data['Close'], columns=ticker_liste_all)
            except:
                bulk_close = pd.DataFrame()

        for _, row in df_port.iterrows():
            symbol = row['Symbol']
            
            # Historie direkt lokal aus dem geladenen DataFrame ziehen
            hist = pd.DataFrame()
            if not bulk_close.empty and symbol in bulk_close.columns:
                hist = pd.DataFrame(bulk_close[symbol].dropna())
                hist.columns = ['Close']
                # Erzeuge High/Low Spalten als Fallback für die Fibo-Logik weiter unten
                hist['High'] = hist['Close']
                hist['Low'] = hist['Close']

            # Lokaler Notfall-Fallback, falls ein Ticker im Massendownload fehlte
            if hist.empty:
                try:
                    hist = yf.Ticker(symbol).history(period="3y")
                except:
                    hist = pd.DataFrame()

            if not hist.empty:
                price = hist['Close'].iloc[-1]
                est_target, pct_change = get_ticker_metadata(symbol)
                
                # Währungsumrechnungen
                cost_per_share = row['AvgCost']
                target = row['TargetPrice']
                if row['Currency'] == 'EUR': 
                    rate = get_exchange_rate()
                    cost_per_share /= rate
                    target /= rate
                    
                current_val = row['Shares'] * price
                current_cost = row['Shares'] * cost_per_share
                current_target = row['Shares'] * target

                total_depot_value  += current_val
                total_depot_cost   += current_cost
                total_depot_target += current_target

                diff_target_abs = abs(target - price)
                diff_target_pct = abs(target - price) / price if price != 0 else 0
                
                # CAGR Berechnung
                days_held = (datetime.now() - row['PurchaseDate'].to_pydatetime().replace(tzinfo=None)).days
                years_held = max(days_held / 365.25, 0.01)
                cagr = ((current_val / current_cost) ** (1 / years_held) - 1) * 100
                
                # Trends direkt im RAM ohne Internet-Anfrage kalkulieren
                trends = {
                    "1D": pct_change if pct_change is not None else 0,
                    "3D": ((price / hist['Close'].iloc[-3]) - 1) * 100 if len(hist) >= 3 else 0,
                    "5D": ((price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0,
                    "1M": ((price / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0,
                    "6M": ((price / hist['Close'].iloc[0]) - 1) * 100 if len(hist) > 0 else 0
                }
                
                res = {
                    "Symbol": symbol, "🌐 Price": price, "Change %": pct_change, 
                    "Est Target": est_target, "Upside %": ((est_target / price) - 1) * 100 if est_target else 0, 
                    "📈 Target": target, "Target %": diff_target_pct * 100, "Target $": diff_target_abs,
                    "📈 Total %": ((current_val/current_cost)-1)*100, "Ø CAGR": cagr
                }
                res.update(trends)
                results_temp.append({"data": res, "hist": hist})

        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_depot_value
        st.session_state.total_depot_cost = total_depot_cost
        st.session_state.total_depot_target = total_depot_target
        st.session_state.ticker_liste = [x['data']['Symbol'] for x in results_temp]

    all_results = st.session_state.all_results
    
    # --- 1. KPI DASHBOARD ---
    st.subheader("Depot Metrics & Status")
    st.caption(f"✨ **{len(df_port):,} Symbols** inside `{current_portfolio_name}` • Parallel Live Mass-Feed •")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="custom-info-box"><h3>Actual</h3><p>{st.session_state.total_depot_value:,.0f} $</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-info-box"><h3>Cost</h3><p>{st.session_state.total_depot_cost:,.0f} $</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="custom-info-box"><h3>Target</h3><p>{st.session_state.total_depot_target:,.0f} $</p></div>', unsafe_allow_html=True)        

    # --- 2. PERFORMANCE TABELLE ---
    st.subheader("Performance & Trends")
 
    if 'all_results' in st.session_state and len(st.session_state.all_results) > 0:
        summary_df = pd.DataFrame([x['data'] for x in st.session_state.all_results])
        
        percent_cols = ['📈 Total %', 'Change %', 'Upside %', 'Ø CAGR', "Target %", '1D', '3D', '5D', '1M', '6M']
        format_dict = {col: "{:.2f}%" for col in percent_cols}
        format_dict["📈 Target"] = "{:.0f} $"
        format_dict["Target $"] = "{:.0f} $"
        format_dict["Est Target"] = "{:.0f} $"
        format_dict["🌐 Price"] = "{:.1f} $"

        actual_format_dict = {k: v for k, v in format_dict.items() if k in summary_df.columns}
        safe_percent_cols = [c for c in percent_cols if c in summary_df.columns]
        summary_df[safe_percent_cols] = summary_df[safe_percent_cols].fillna(0)

        try:
            st.dataframe(
                summary_df.style.format(actual_format_dict, na_rep='-')
                .set_properties(**{'background-color': 'white', 'color': 'black'})
                .background_gradient(cmap='RdYlGn', subset=safe_percent_cols),
                use_container_width=True
            )
        except Exception as e:
            st.dataframe(summary_df, use_container_width=True)
            st.caption(f"Hint: Table-Styling deactivated ({e})")   
    
    # --- 3. TECHNICAL DETAIL ANALYSE ---
    st.divider()
    st.subheader("🔍 Technical Detail-Analysis")
    
    if "fib_start" not in st.session_state:
        st.session_state["fib_start"] = None
        st.session_state["fib_end"] = None
        st.session_state["fibo_trend_analyse"] = True

    ticker_liste = st.session_state.get('ticker_liste', [])

    if ticker_liste:
        if 'ticker_index' not in st.session_state:
            st.session_state.ticker_index = 0

        def move_next():
            st.session_state.ticker_index = (st.session_state.ticker_index + 1) % len(ticker_liste)
            st.session_state.sb_selector = ticker_liste[st.session_state.ticker_index]

        def move_prev():
            st.session_state.ticker_index = (st.session_state.ticker_index - 1) % len(ticker_liste)
            st.session_state.sb_selector = ticker_liste[st.session_state.ticker_index]
        
        def sync_index():
            st.session_state.ticker_index = ticker_liste.index(st.session_state.sb_selector)

        col_prev, col_select, col_next = st.columns([1, 3, 1])
        with col_prev:
            st.button("⬅️ Prev", on_click=move_prev, key="nav_prev", use_container_width=True)
        with col_next:
            st.button("Next ➡️", on_click=move_next, key="nav_next", use_container_width=True)
        with col_select:
            st.selectbox(
                "Symbol", options=ticker_liste, index=st.session_state.ticker_index,
                key="sb_selector", on_change=sync_index, label_visibility="collapsed"
            )

        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == ticker_liste[st.session_state.ticker_index]), None) 
        
        if pick:
            # Falls für diesen Ticker beim Einzelabruf tiefergehende historische High/Low-Daten nötig sind:
            if 'High' not in pick['hist'].columns or pick['hist']['High'].equals(pick['hist']['Close']):
                try:
                    # Holt tiefere Candlestick-Daten nur für das aktuell selektierte Detail-Asset
                    pick['hist'] = yf.Ticker(pick['data']['Symbol']).history(period="3y")
                except:
                    pass

            hist_full = pick['hist'].copy()
            hist_full.index = hist_full.index.tz_localize(None)
            selected_ticker = pick['data']['Symbol']

            st.write(f"### 📈 {selected_ticker} - Analyze in time frame")

            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]

            if st.session_state["fib_start"] not in month_options:
                st.session_state["fib_start"] = month_options[0]
            if st.session_state["fib_end"] not in month_options:
                st.session_state["fib_end"] = month_options[-1]
                        
            cols = st.columns([0.5, 1.5, 0.5, 1.5, 1.5], vertical_alignment="center")
            cols[0].markdown("**Start**")
            sel_start = cols[1].selectbox("Start", options=month_options, index=month_options.index(st.session_state["fib_start"]), label_visibility="collapsed", key="ui_start")
            cols[2].markdown("**End**")
            sel_end = cols[3].selectbox("End", options=month_options, index=month_options.index(st.session_state["fib_end"]), label_visibility="collapsed", key="ui_end")

            if cols[4].button(f"🔍 Analyse Range", help="Analyse Fibonacci levels on the selected time range."):
                st.session_state["fib_start"] = sel_start
                st.session_state["fib_end"] = sel_end
                st.session_state["fibo_trend_analyse"] = True

            # Analyse-Zeitfenster filtern
            fib_mask = (hist_full.index >= pd.to_datetime(st.session_state["fib_start"])) & (hist_full.index <= (pd.to_datetime(st.session_state["fib_end"]) + pd.offsets.MonthEnd(0)))
            plot_hist = hist_full.loc[fib_mask]
            
            fib_trends = find_multiple_trends(plot_hist, max_trends=4, strong_threshold=0.05)
            render_multi_trend_alert_box(fib_trends, selected_ticker)
                                       
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

            if st.session_state.get("fibo_trend_inspect", False):
                st.plotly_chart(create_chart(selected_ticker, plot_hist, dynamic_fibs, fib_trends), use_container_width=True)
            else:
                chart_col, sidebar_col = st.columns([4, 1])
                with chart_col:
                    st.plotly_chart(create_chart(selected_ticker, plot_hist, dynamic_fibs, fib_trends), use_container_width=True)            

                with sidebar_col:
                    st.write(f"### {selected_ticker} - Key Metrics")
                    curr_p = pick['data']['🌐 Price']
                    
                    try:
                        s_obj = yf.Ticker(selected_ticker)
                        target = s_obj.info.get('targetMeanPrice')
                        if target:
                            up_val = ((target / curr_p) - 1) * 100
                            if up_val > 0:
                                st.markdown(f'<div style="background-color: #e6f4ea; color: #137333; padding: 8px; border-radius: 4px; font-weight: bold;">1Y Target Estimate: {target:.2f} $<br>↑ {up_val:.1f}% Upside from {curr_p:.2f} $</div>', unsafe_allow_html=True)
                            else:       
                                st.markdown(f'<div style="background-color: #fce8e6; color: #c5221f; padding: 8px; border-radius: 4px; font-weight: bold;">1Y Target Estimate: {target:.2f} $<br>↓ {abs(up_val):.1f}% Downside from {curr_p:.2f} $</div>', unsafe_allow_html=True)   
                    except:
                        st.caption("Analyst-Target not available")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.subheader(f"Fibonacci Levels")
                    st.caption(f"Calculated from {st.session_state['fib_start']} to {st.session_state['fib_end']}")
                    
                    for label, val in dynamic_fibs.items():
                        prox = abs(curr_p - val) / val * 100
                        prefix = "🎯" if prox < 1.5 else "⚪"
                        st.write(f"{prefix} **{label}: {val:.2f}**")
        else:
            st.error("No data available for this time frame.")