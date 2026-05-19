import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import calendar
from datetime import datetime
import numpy as np
from scipy.signal import argrelextrema
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

def find_multiple_trends(df, max_trends=4, strong_threshold=0.05, order=10):
    """Findet signifikante Trends über lokale Swing Highs und Lows."""
    trends = []
    if df is None or df.empty or 'Close' not in df.columns:
        return trends
        
    prices = df['Close'].values
    dates = pd.to_datetime(df.index).tz_localize(None)
    
    total_len = len(prices)
    if total_len < 15:
        return trends

    if total_len < 40:
        order = 3
    elif total_len < 100:
        order = 5

    local_max_idx = argrelextrema(prices, np.greater, order=order)[0]
    local_min_idx = argrelextrema(prices, np.less, order=order)[0]
    
    all_extrema = sorted(list(local_max_idx) + list(local_min_idx))
    
    if len(all_extrema) < 2:
        all_extrema = [0, total_len - 1]
    else:
        if all_extrema[0] != 0:
            all_extrema.insert(0, 0)
        if all_extrema[-1] != total_len - 1:
            all_extrema.append(total_len - 1)

    raw_legs = []
    for i in range(len(all_extrema) - 1):
        idx_start = all_extrema[i]
        idx_end = all_extrema[i+1]
        
        if idx_end - idx_start < 2:
            continue
            
        p_start = prices[idx_start]
        p_end = prices[idx_end]
        
        if p_start == 0:
            continue
            
        move_pct = abs(p_end - p_start) / p_start
        
        if move_pct >= strong_threshold:
            raw_legs.append({
                "f_start": dates[idx_start],
                "f_end": dates[idx_end],
                "price_start": p_start,
                "price_end": p_end,
                "move_pct": move_pct,
                "type": "Bullish" if p_start < p_end else "Bearish"
            })
            
    sorted_legs = sorted(raw_legs, key=lambda x: x["move_pct"], reverse=True)
    
    for idx, leg in enumerate(sorted_legs[:max_trends]):
        leg["id"] = f"T{idx+1}"
        trends.append(leg)
        
    return trends


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
            df = pd.read_csv("Sample-Portfolio.csv", sep=';')
            filename = "Sample-Portfolio.csv"
        except Exception as e:
            st.error(f"Datei 'Sample-Portfolio.csv' nicht gefunden: {e}")
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
    div_yield = 0.0
    try:
        info = stock.info
        if info:
            pct_change = info.get('regularMarketChangePercent', 0)
            est_target = info.get('targetMeanPrice')
            div_yield = info.get('dividendYield', 0)
            if div_yield is None:
                div_yield = 0.0
    except:
        pass
    return est_target, pct_change, div_yield


# --- CHARTING ---

def create_chart(ticker, hist, fibs, f_trends, inspect_active):
    fig = go.Figure()
    if hist is None or hist.empty:
        return fig

    hist.index = hist.index.tz_localize(None)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Kurs", line=dict(color='#1f77b4', width=2)))

    fibo_colors = ['#d62728', '#ff7f0e', '#2ca02c', '#ff7f0e', '#d62728']
    for (label, val), color in zip(fibs.items(), fibo_colors):
        fig.add_hline(y=val, line_dash="dash", line_color=color, annotation_text=label)
        
    fig.update_layout(template="plotly_white", height=420, margin=dict(l=20, r=20, t=20, b=20))

    if inspect_active and f_trends:
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

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

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
    if 'current_loaded_name' not in st.session_state or st.session_state.current_loaded_name != current_portfolio_name:
        st.session_state.current_loaded_name = current_portfolio_name
        results_temp = []
        total_depot_value = 0.0
        total_depot_cost = 0.0
        total_depot_target = 0.0    

        ticker_liste_all = df_port['Symbol'].unique().tolist()
        
        with st.spinner("Hole alle Live-Marktdaten parallel von Yahoo Finance..."):
            try:
                bulk_data = yf.download(ticker_liste_all, period="3y", progress=False)
                bulk_close = bulk_data['Close'] if len(ticker_liste_all) > 1 else pd.DataFrame(bulk_data['Close'], columns=ticker_liste_all)
            except:
                bulk_close = pd.DataFrame()

        for _, row in df_port.iterrows():
            symbol = row['Symbol']
            
            hist = pd.DataFrame()
            if not bulk_close.empty and symbol in bulk_close.columns:
                hist = pd.DataFrame(bulk_close[symbol].dropna())
                hist.columns = ['Close']
                hist['High'] = hist['Close']
                hist['Low'] = hist['Close']

            if hist.empty:
                try:
                    hist = yf.Ticker(symbol).history(period="3y")
                except:
                    hist = pd.DataFrame()

            if not hist.empty:
                price = hist['Close'].iloc[-1]
                est_target, pct_change, div_yield = get_ticker_metadata(symbol)
                
                cost_per_share = row['AvgCost']
                
                target = row['TargetPrice']
                if row['Currency'] == 'EUR': 
                    rate = get_exchange_rate()
                    cost_per_share /= rate
                    target /= rate

                current_shares = row['Shares']
                current_val = row['Shares'] * price
                current_cost = row['Shares'] * cost_per_share
                current_target = row['Shares'] * target

                total_depot_value  += current_val
                total_depot_cost   += current_cost
                total_depot_target += current_target

                diff_target_abs = abs(target - price)
                diff_target_pct = abs(target - price) / price if price != 0 else 0
                
                # --- ROBUSTE DATUMS- & CAGR-BERECHNUNG ---
                purchase_date = row['PurchaseDate']
                if pd.isna(purchase_date) or isinstance(purchase_date, str):
                    try:
                        purchase_date = pd.to_datetime(purchase_date)
                    except:
                        purchase_date = None

                if purchase_date is None or pd.isna(purchase_date):
                    days_held = 365
                else:
                    p_date_naive = purchase_date.to_pydatetime().replace(tzinfo=None)
                    days_held = max((datetime.now() - p_date_naive).days, 1)
                
                years_held = max(days_held / 365.25, 0.01)
                cagr = ((current_val / current_cost) ** (1 / years_held) - 1) * 100
                
                trends = {
                    "1D": pct_change if pct_change is not None else 0,
                    "3D": ((price / hist['Close'].iloc[-3]) - 1) * 100 if len(hist) >= 3 else 0,
                    "5D": ((price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) >= 5 else 0,
                    "1M": ((price / hist['Close'].iloc[-21]) - 1) * 100 if len(hist) >= 21 else 0,
                    "6M": ((price / hist['Close'].iloc[0]) - 1) * 100 if len(hist) > 0 else 0
                }
                
                res = {
                    "Symbol": symbol, "🌐 Price": price, "Change %": pct_change, "Div Yield": div_yield,
                    "Est Target": est_target, "Upside %": ((est_target / price) - 1) * 100 if est_target else 0, 
                    "Shares": current_shares, "Cost/Share": cost_per_share, "PurchaseDate": purchase_date.strftime('%Y-%m-%d') if purchase_date is not None else "Unknown",
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
        st.markdown(f'<div class="custom-info-box"><h3>Actual Asset Value</h3><p>{st.session_state.total_depot_value:,.2f} $</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-info-box"><h3>Invested Cost Base</h3><p>{st.session_state.total_depot_cost:,.2f} $</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="custom-info-box"><h3>Aggregated Target Value</h3><p>{st.session_state.total_depot_target:,.2f} $</p></div>', unsafe_allow_html=True)        

    # --- 2. PERFORMANCE TABELLE MIT KLICK-AUSWAHL ---
    st.subheader("Performance Matrix & Trend Analytics")
    st.caption("💡 *Klicke auf eine Zeile in der Tabelle, um die technische Detail-Analyse direkt für diesen Ticker zu öffnen.*")
 
    if 'all_results' in st.session_state and len(st.session_state.all_results) > 0:
        summary_df = pd.DataFrame([x['data'] for x in st.session_state.all_results])
        
        percent_cols = ['📈 Total %', 'Change %', 'Upside %', 'Ø CAGR', 'Target %', '1D', '3D', '5D', '1M', '6M']
        format_dict = {col: "{:.2f}%" for col in percent_cols}
        format_dict["Div Yield"] = "{:.1f}%"
        format_dict["📈 Target"] = "{:.2f} $"
        format_dict["Target $"] = "{:.2f} $"
        format_dict["Est Target"] = "{:.2f} $"
        format_dict["Cost/Share"] = "{:.2f} $"
        format_dict["🌐 Price"] = "{:.2f} $"

        actual_format_dict = {k: v for k, v in format_dict.items() if k in summary_df.columns}
        safe_percent_cols = [c for c in percent_cols + ["Div Yield"] if c in summary_df.columns]
        summary_df[safe_percent_cols] = summary_df[safe_percent_cols].fillna(0)

        event = st.dataframe(
            summary_df.style.format(actual_format_dict, na_rep='-')
            .set_properties(**{'background-color': 'white', 'color': 'black'})
            .background_gradient(cmap='RdYlGn', subset=[c for c in safe_percent_cols if c != 'Div Yield']),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if event and 'rows' in event.selection and len(event.selection['rows']) > 0:
            selected_row_idx = event.selection['rows'][0]
            if 'ticker_index' not in st.session_state or st.session_state.ticker_index != selected_row_idx:
                st.session_state.ticker_index = selected_row_idx
                st.session_state["fibo_needs_refresh"] = True

    # --- 3. HYBRIDE DETAILANALYSE (VISUELL SOFORT / MATHEMATISCH STARR) ---
    st.divider()
    
    ticker_liste = st.session_state.get('ticker_liste', [])

    if ticker_liste:
        if 'ticker_index' not in st.session_state or st.session_state.ticker_index >= len(ticker_liste):
            st.session_state.ticker_index = 0
            st.session_state["fibo_needs_refresh"] = True

        selected_ticker = ticker_liste[st.session_state.ticker_index]
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == selected_ticker), None) 
        
        if pick:
            if 'High' not in pick['hist'].columns or pick['hist']['High'].equals(pick['hist']['Close']):
                try:
                    pick['hist'] = yf.Ticker(pick['data']['Symbol']).history(period="3y")
                except:
                    pass

            hist_full = pick['hist'].copy()
            hist_full.index = hist_full.index.tz_localize(None)

            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]

            # Mathematischer Analyse-Zustand im State verankern
            if "calc_fib_start" not in st.session_state or st.session_state["calc_fib_start"] not in month_options:
                st.session_state["calc_fib_start"] = month_options[0]
            if "calc_fib_end" not in st.session_state or st.session_state["calc_fib_end"] not in month_options:
                st.session_state["calc_fib_end"] = month_options[-1]

            # Visueller Live-Zustand für den interaktiven Sofort-Zuschnitt des Charts
            if "ui_fib_start" not in st.session_state or st.session_state["ui_fib_start"] not in month_options:
                st.session_state["ui_fib_start"] = st.session_state["calc_fib_start"]
            if "ui_fib_end" not in st.session_state or st.session_state["ui_fib_end"] not in month_options:
                st.session_state["ui_fib_end"] = st.session_state["calc_fib_end"]
                
            # Bei Tickerwechsel alles hart auf Maximum zurücksetzen und neu berechnen
            if st.session_state.get("fibo_needs_refresh", True):
                st.session_state["calc_fib_start"] = month_options[0]
                st.session_state["calc_fib_end"] = month_options[-1]
                st.session_state["ui_fib_start"] = month_options[0]
                st.session_state["ui_fib_end"] = month_options[-1]
                st.session_state["fibo_needs_refresh"] = False

            top_layout_left, top_layout_right = st.columns([3, 1], vertical_alignment="bottom")
            
            with top_layout_left:
                st.markdown(f"#### 🛠️ Time Window Selection for {selected_ticker}")
                
                idx_ui_start = month_options.index(st.session_state["ui_fib_start"])
                idx_ui_end = month_options.index(st.session_state["ui_fib_end"])
                
                btn_start_clicked = False
                btn_end_clicked = False

                t_col_start_sel, t_col_start_btn, t_col_end_btn, t_col_end_sel, t_col_action = st.columns(
                    [2.0, 0.5, 0.5, 2.0, 1.5], 
                    vertical_alignment="bottom"
                )
                
                # 1. BUTTON-LOGIK (Prüfung vor den Selectboxen)
                with t_col_start_btn:
                    if st.button(">>", help="Startfenster um 3 Monate verengen", use_container_width=True):
                        new_idx = min(idx_ui_start + 3, idx_ui_end)
                        st.session_state["ui_fib_start"] = month_options[new_idx]
                        btn_start_clicked = True

                with t_col_end_btn:
                    if st.button("<<", help="Endfenster um 3 Monate verengen", use_container_width=True):
                        new_idx = max(idx_ui_end - 3, idx_ui_start)
                        st.session_state["ui_fib_end"] = month_options[new_idx]
                        btn_end_clicked = True

                if btn_start_clicked or btn_end_clicked:
                    st.rerun()

                # 2. SELECTBOXEN
                with t_col_start_sel:
                    sel_start = st.selectbox(
                        "Start Window", 
                        options=month_options, 
                        index=month_options.index(st.session_state["ui_fib_start"]), 
                        key="sel_start_ui"
                    )
                    st.session_state["ui_fib_start"] = sel_start
                
                with t_col_end_sel:
                    sel_end = st.selectbox(
                        "End Window", 
                        options=month_options, 
                        index=month_options.index(st.session_state["ui_fib_end"]), 
                        key="sel_end_ui"
                    )
                    st.session_state["ui_fib_end"] = sel_end
                
                # 3. ANALYSE BUTTON
                with t_col_action:
                    if st.button("🔍 Analyse Range", use_container_width=True):
                        st.session_state["calc_fib_start"] = st.session_state["ui_fib_start"]
                        st.session_state["calc_fib_end"] = st.session_state["ui_fib_end"]

            # --- DATEN-SPLIT FÜR HYBRIDES VERHALTEN ---
            # A. Mathematische Analyse basiert starr auf den berechneten "calc_fib"-Werten
            calc_mask = (hist_full.index >= pd.to_datetime(st.session_state["calc_fib_start"])) & (hist_full.index <= (pd.to_datetime(st.session_state["calc_fib_end"]) + pd.offsets.MonthEnd(0)))
            calc_hist = hist_full.loc[calc_mask]
            fib_trends = find_multiple_trends(calc_hist, max_trends=4, strong_threshold=0.05)

            h = 0 if calc_hist.empty else calc_hist['High'].max()
            l = 0 if calc_hist.empty else calc_hist['Low'].min()
            d = h - l
            
            dynamic_fibs = {
                "0% (High)": h,
                "38.2% Retracement": h - 0.382 * d,
                "50.0% Center Line": h - 0.5 * d,
                "61.8% Golden Pocket": h - 0.618 * d,
                "100% (Low Base)": l
            }

            # B. Der gezeichnete Kursverlauf (X-Achse) reagiert SOFORT auf das Live-UI Fenster
            vis_mask = (hist_full.index >= pd.to_datetime(st.session_state["ui_fib_start"])) & (hist_full.index <= (pd.to_datetime(st.session_state["ui_fib_end"]) + pd.offsets.MonthEnd(0)))
            vis_hist = hist_full.loc[vis_mask]

            main_trend_type = fib_trends[0]["type"] if fib_trends else "Bullish"
            chart_icon = "📈" if main_trend_type == "Bullish" else "📉"
            
            st.markdown("---")
            st.subheader(f"{chart_icon} {selected_ticker} - Technical Analysis View")

            if fib_trends:
                main_trend = fib_trends[0]
                banner_text = f"**{selected_ticker} Analyzed Trend {main_trend['type']}** {main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} ({main_trend['move_pct']*100:.1f}%). {len(fib_trends)} trends detected."
                if main_trend['type'] == "Bullish":
                    st.success(f"🚀 {banner_text}")
                else:
                    st.info(f"🤖 {banner_text}")

            with top_layout_right:
                st.markdown(f"**Selected Asset:** `{selected_ticker}`")
                inspect_active = st.toggle("📈 Visualize Trends Overlay", value=True, key="fibo_trend_inspect")

            chart_col, sidebar_col = st.columns([3, 1])
            with chart_col:
                # Der Chart kriegt die Live-Zuschnitts-Historie (vis_hist), behält aber die fixen Berechnungen
                st.plotly_chart(create_chart(selected_ticker, vis_hist, dynamic_fibs, fib_trends, inspect_active), use_container_width=True)            
            
            with sidebar_col:
                curr_p = pick['data']['🌐 Price']
                
                # --- GENERIERUNG DES DOWNLOADABLE DATA-DUMPS (VARIANTE B) ---
                detected_trends_str = ""
                if fib_trends:
                    for t in fib_trends:
                        detected_trends_str += f"- {t['id']} ({t['type']}): {t['f_start'].strftime('%Y-%m-%d')} to {t['f_end'].strftime('%Y-%m-%d')} (Move: {t['move_pct']*100:.1f}%)\n"
                else:
                    detected_trends_str = "- Keine signifikanten Trends detektiert.\n"

                fib_levels_str = ""
                for label, val in dynamic_fibs.items():
                    fib_levels_str += f"- {label}: {val:.2f} $\n"

                gemini_data_dump = f"""[TECHNICAL ANALYSIS EXPORT: {selected_ticker}]
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Calculated Analysis Basis: {st.session_state['calc_fib_start']} to {st.session_state['calc_fib_end']}
Current Price: {curr_p:.2f} $
1Y Mean Target estimate: {pick['data']['Est Target']:.2f} $ (Upside: {pick['data']['Upside %']:.1f}%)
Purchased {pick['data']['Shares']} shares on {pick['data']['PurchaseDate']} @ {pick['data']['Cost/Share']:.2f} $

Detected Trends:
{detected_trends_str}
Fibonacci Levels:
{fib_levels_str}"""

                # Der native, hochkompakte Download-Button, der das UI-Design schont
                st.download_button(
                    label="📸 Export Dataset for Gemini",
                    data=gemini_data_dump,
                    file_name=f"gemini_analysis_{selected_ticker}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Lädt einen kompakten Datensatz herunter, den du direkt an Gemini senden kannst."
                )

                st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
                st.markdown(f"##### Key Metrics")
                
                try:
                    s_obj = yf.Ticker(selected_ticker)
                    target = s_obj.info.get('targetMeanPrice')
                    if target:
                        up_val = ((target / curr_p) - 1) * 100
                        if up_val > 0:
                            st.markdown(f"""
                                <div style="background-color: #e6f4ea; color: #137333; padding: 10px; border-radius: 4px; font-weight: bold; font-size:13px;">
                                    1Y Target Estimate: {target:.2f} $<br>↑ {up_val:.1f}% Upside from {curr_p:.2f} $
                                </div>
                            """, unsafe_allow_html=True)
                        else:       
                            st.markdown(f"""
                                <div style="background-color: #fce8e6; color: #c5221f; padding: 10px; border-radius: 4px; font-weight: bold; font-size:13px;">
                                    1Y Target Estimate: {target:.2f} $<br>↓ {abs(up_val):.1f}% Downside from {curr_p:.2f} $
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("Analyst-Target data not loaded")
                except:
                    st.caption("Analyst-Target not available")

                if pick['data']['Div Yield'] > 0:
                    st.markdown(f"""
                        <div style="background-color: #e8f0fe; color: #1a73e8; padding: 10px; border-radius: 4px; font-weight: bold; font-size:13px; margin-top:5px;">
                            💵 Live Dividend Yield: {pick["data"]["Div Yield"]:.1f}%
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
                st.markdown("##### Fibonacci Levels")
                st.caption(f"Calculated Basis: {st.session_state['calc_fib_start']} to {st.session_state['calc_fib_end']}")
                
                for label, val in dynamic_fibs.items():
                    prox = abs(curr_p - val) / val * 100
                    prefix = "🎯" if prox < 1.5 else "⚪"
                    st.write(f"{prefix} **{label}:** {val:.2f}")
        else:
            st.error("Gefundener Ticker konnte im Speicher nicht validiert werden.")