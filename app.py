import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import calendar
from datetime import datetime
import numpy as np
from scipy.signal import find_peaks
from scipy.signal import argrelextrema
import sys
import os

# --- CONFIGURATION & THEME ---
st.set_page_config(
    page_title="Portfolio Architektur Pro",
    page_icon="📈",
    layout="wide"
)

# Centralized CSS for styling and UI optimization
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
    /* Macht den File Uploader extrem kompakt für die Inline-Anzeige */
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
    """Extracts the filename if passed via '-f <filename>' in the terminal."""
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


# --- CORE ALGORITHMS ---

def find_multiple_trends(df, max_trends=4, strong_threshold=0.05, order=10):
    """
    Finds significant trends by analyzing sequential local swing highs and lows.
    'order' controls the window size (e.g., 10 days on each side to confirm a peak).
    """
    trends = []
    if df is None or df.empty or 'Close' not in df.columns:
        return trends
        
    prices = df['Close'].values
    dates = pd.to_datetime(df.index).tz_localize(None)
    
    if len(prices) < 15:
        return trends

    # 1. Find local peaks and troughs
    # order=10 means a point must be higher/lower than 10 points before and after it
    local_max_idx = argrelextrema(prices, np.greater, order=order)[0]
    local_min_idx = argrelextrema(prices, np.less, order=order)[0]
    
    # 2. Combine and sort them chronologically to map the market's zigzag geometry
    all_extrema = sorted(list(local_max_idx) + list(local_min_idx))
    
    if len(all_extrema) < 2:
        # Fallback to absolute endpoints if no local extrema are prominent enough
        all_extrema = [0, len(prices) - 1]

    # 3. Scan consecutive local turning points for significant legs
    raw_legs = []
    for i in range(len(all_extrema) - 1):
        idx_start = all_extrema[i]
        idx_end = all_extrema[i+1]
        
        # Enforce minimum distance between peaks/troughs if desired
        if idx_end - idx_start < 3:
            continue
            
        p_start = prices[idx_start]
        p_end = prices[idx_end]
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
            
    # 4. Sort all identified moves by intensity/magnitude
    sorted_legs = sorted(raw_legs, key=lambda x: x["move_pct"], reverse=True)
    
    # 5. Extract top configurations up to max_trends
    for idx, leg in enumerate(sorted_legs[:max_trends]):
        leg["id"] = f"T{idx+1}"
        trends.append(leg)
        
    return trends

def XXX_find_multiple_trends(df, max_trends=4, strong_threshold=0.05):
    """Finds the dominant trend and up to 3 significant sub-trends with correct datetime mapping."""
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


# --- DATA RETRIEVAL ---

def load_portfolio(uploaded_file):
    """Loads portfolio from uploaded file, CLI arguments, or falls back to local defaults."""
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
        except:
            df = pd.read_csv("Sample-Portfolio.csv", sep=';')
            filename = "Sample-Portfolio.csv"
                
        df['PurchaseDate'] = pd.to_datetime(df['PurchaseDate'])
        return df, filename
    except Exception as e:
        st.error(f"Error loading portfolio layout: {e}")
        return None, "No Portfolio Loaded"


def get_exchange_rate():
    try:
        fx = yf.Ticker("EURUSD=X")
        return 1 / fx.history(period="1d")['Close'].iloc[-1]
    except:
        return 0.92


@st.cache_data(ttl=3600)
def get_ticker_data(ticker_symbol):
    """Fetches stock price metrics, trend percentages, and dividend metrics (Cached for API speed)."""
    stock = yf.Ticker(ticker_symbol)
    current_price = None
    est_target = None
    upside = pct_change = 0
    div_yield = 0.0
    trends = {"1D": 0, "3D": 0, "5D": 0, "1M": 0, "6M": 0}
    
    try:
        info = stock.info
        if info:
            pct_change = info.get('regularMarketChangePercent', 0)
            current_price = info.get('regularMarketPrice') or info.get('currentPrice')
            est_target = info.get('targetMeanPrice')
            div_yield = info.get('dividendYield', 0)
            if div_yield is None:
                div_yield = 0.0
            div_yield *= 100
            
            if est_target and current_price:
                upside = ((est_target / current_price) - 1) * 100
    except:
        pass
        
    try:
        hist_short = stock.history(period="1mo")
        if not hist_short.empty and len(hist_short) >= 5:
            cp = hist_short['Close'].iloc[-1]
            trends["1D"] = pct_change if pct_change is not None else 0
            trends["3D"] = ((cp / hist_short['Close'].iloc[-3]) - 1) * 100
            trends["5D"] = ((cp / hist_short['Close'].iloc[-5]) - 1) * 100
            trends["1M"] = ((cp / hist_short['Close'].iloc[0]) - 1) * 100
    except:
        pass
    
    return current_price, est_target, upside, pct_change, trends, div_yield


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


# --- MAIN APPLICATION INTERFACE ---

st.title("🏛️ Pero Portfolio & Trend Analyzer")

# State tracking for uploader unique identity key
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# Spalten für Kopfzeilen-Layout (Workspace links, Upload daneben, Löschen ganz rechts)
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
        if st.button("❌", help="Reset to standard portfolios"):
            st.session_state.uploader_key += 1
            if is_cli_active:
                sys.argv = [a for a in sys.argv if a != "-f" and a != current_portfolio_name]
            st.rerun()

st.markdown("---")

if df_port is not None:
    if 'current_loaded_name' not in st.session_state or st.session_state.current_loaded_name != current_portfolio_name:
        st.session_state.current_loaded_name = current_portfolio_name
        results_temp = []
        total_depot_value = 0.0
        total_depot_cost = 0.0
        total_depot_target = 0.0    

        # Extrahiere alle eindeutigen Symbole und lade den 3-Jahres-Verlauf parallel herunter
        ticker_liste_all = df_port['Symbol'].unique().tolist()
        
        with st.spinner("Hole Live-Marktdaten parallel von Yahoo Finance..."):
            try:
                bulk_hist = yf.download(ticker_liste_all, period="3y", group_by='ticker', progress=False)
            except:
                bulk_hist = pd.DataFrame()

        for _, row in df_port.iterrows():
            symbol = row['Symbol']
            
            # Basis-Daten (Dividenden, Targets) aus dem schnellen Cache holen
            price_api, est_target, upside, pct_change, trends, div_yield = get_ticker_data(symbol)
            
            # Extrahiere die Historie für diesen spezifischen Ticker aus dem Bulk-Datensatz
            hist = None
            if not bulk_hist.empty:
                try:
                    if len(ticker_liste_all) == 1:
                        hist = bulk_hist.dropna(subset=['Close'])
                    else:
                        hist = bulk_hist[symbol].dropna(subset=['Close'])
                except:
                    hist = None

            # FIX: Bereinigte Fallback-Bedingung ohne fehlerhaften Walrus-Operator
            if hist is None or hist.empty:
                try:
                    hist = yf.Ticker(symbol).history(period="3y")
                except:
                    hist = pd.DataFrame()

            if hist is not None and not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                price = price_api

            if price and hist is not None and not hist.empty:
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
                diff_target_pct = (abs(target - price) / price if price != 0 else 0) * 100
                
                # Berechnung der Haltedauer in Tagen
                purchase_date = row['PurchaseDate']
                if pd.isna(purchase_date):
                    days_held = 365
                else:
                    days_held = (datetime.now() - purchase_date.to_pydatetime().replace(tzinfo=None)).days
                
                years_held = max(days_held / 365.25, 0.01)
                cagr = ((current_val / current_cost) ** (1 / years_held) - 1) * 100
                
                if "6M" not in trends or trends["6M"] == 0:
                    trends["6M"] = ((price / hist['Close'].iloc[0]) - 1) * 100 if len(hist) > 0 else 0

                res = {
                    "Symbol": symbol, 
                    "🌐 Price": price, 
                    "Div Yield": div_yield,
                    "Change %": pct_change, 
                    "Est Target": est_target, 
                    "Upside %": upside, 
                    "📈 Target": target,
                    "Target %": diff_target_pct, 
                    "Target $": diff_target_abs,
                    "📈 Total %": ((current_val/current_cost)-1)*100, 
                    "Ø CAGR": cagr
                }
                res.update(trends)
                results_temp.append({"data": res, "hist": hist})

        st.session_state.all_results = results_temp
        st.session_state.total_depot_value = total_depot_value
        st.session_state.total_depot_cost = total_depot_cost
        st.session_state.total_depot_target = total_depot_target
        st.session_state.ticker_liste = [x['data']['Symbol'] for x in results_temp]

    all_results = st.session_state.all_results
    
    # 1. KPI DASHBOARD
    st.subheader("Depot Metrics & Status")
    st.caption(f"✨ **{len(df_port):,} Symbols** inside `{current_portfolio_name}` • Live Market Feeds Feeded •")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="custom-info-box"><h3>Actual Asset Value</h3><p>{st.session_state.total_depot_value:,.2f} $</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="custom-info-box"><h3>Invested Cost Base</h3><p>{st.session_state.total_depot_cost:,.2f} $</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="custom-info-box"><h3>Aggregated Target Value</h3><p>{st.session_state.total_depot_target:,.2f} $</p></div>', unsafe_allow_html=True)        

    # 2. PERFORMANCE TABLE WITH SELECTION INTEGRATION
    st.subheader("Performance Matrix & Trend Analytics")
    st.caption("💡 *Click any row inside the list below to directly select it for structural detail-analysis below.*")
 
    if 'all_results' in st.session_state and len(st.session_state.all_results) > 0:
        summary_df = pd.DataFrame([x['data'] for x in st.session_state.all_results])
        
        percent_cols = ['📈 Total %', 'Change %', 'Upside %', 'Ø CAGR', 'Target %', '1D', '3D', '5D', '1M', '6M']
        
        format_dict = {col: "{:.2f}%" for col in percent_cols}
        format_dict["Div Yield"] = "{:.0f}%" 
        format_dict["📈 Target"] = "{:.2f} $"
        format_dict["Target $"] = "{:.2f} $"
        format_dict["Est Target"] = "{:.2f} $"
        format_dict["🌐 Price"] = "{:.2f} $"

        safe_percent_cols = [c for c in percent_cols + ["Div Yield"] if c in summary_df.columns]
        summary_df[safe_percent_cols] = summary_df[safe_percent_cols].fillna(0)

        event = st.dataframe(
            summary_df.style.format(format_dict, na_rep='-')
            .set_properties(**{'background-color': 'white', 'color': 'black'})
            .background_gradient(cmap='RdYlGn', subset=[c for c in safe_percent_cols if c != 'Div Yield']),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        selected_row_idx = 0
        if event and 'rows' in event.selection and len(event.selection['rows']) > 0:
            selected_row_idx = event.selection['rows'][0]
            st.session_state.ticker_index = selected_row_idx

    # --- TECHNICAL BREAKDOWN & TIME RANGE ANALYSIS ---
    st.divider()
    
    ticker_liste = st.session_state.get('ticker_liste', [])

    if ticker_liste:
        if 'ticker_index' not in st.session_state or st.session_state.ticker_index >= len(ticker_liste):
            st.session_state.ticker_index = 0

        selected_ticker = ticker_liste[st.session_state.ticker_index]
        pick = next((item for item in st.session_state.all_results if item['data']['Symbol'] == selected_ticker), None) 
        
        if pick:
            hist_full = pick['hist'].copy()
            hist_full.index = hist_full.index.tz_localize(None)

            available_months = hist_full.index.to_period('M').unique()
            month_options = [d.strftime('%Y-%m') for d in available_months]
            idx_end = len(month_options) - 1

            if "fib_start" not in st.session_state or st.session_state["fib_start"] not in month_options:
                st.session_state["fib_start"] = month_options[0]
            if "fib_end" not in st.session_state or st.session_state["fib_end"] not in month_options:
                st.session_state["fib_end"] = month_options[-1]

            top_layout_left, top_layout_right = st.columns([3, 1], vertical_alignment="bottom")
            
            with top_layout_left:
                st.markdown(f"#### 🛠️ Time Window Selection for {selected_ticker}")
                t_col1, t_col2, t_col3 = st.columns([2, 2, 1.5], vertical_alignment="center")
                
                sel_start = t_col1.selectbox("Start Window", options=month_options, index=month_options.index(st.session_state["fib_start"]), key="sel_start_ui")
                sel_end = t_col2.selectbox("End Window", options=month_options, index=month_options.index(st.session_state["fib_end"]), key="sel_end_ui")
                
                if t_col3.button("🔍 Analyse Range", use_container_width=True):
                    st.session_state["fib_start"] = sel_start
                    st.session_state["fib_end"] = sel_end
                    st.session_state["fibo_trend_analyse"] = True

            fib_mask = (hist_full.index >= pd.to_datetime(st.session_state["fib_start"])) & (hist_full.index <= (pd.to_datetime(st.session_state["fib_end"]) + pd.offsets.MonthEnd(0)))
            fib_hist = hist_full.loc[fib_mask]
            fib_trends = find_multiple_trends(fib_hist, max_trends=4, strong_threshold=0.05)

            main_trend_type = fib_trends[0]["type"] if fib_trends else "Bullish"
            chart_icon = "📈" if main_trend_type == "Bullish" else "📉"
            
            st.markdown("---")
            st.subheader(f"{chart_icon} {selected_ticker} - Analyze in time frame")

            if fib_trends:
                main_trend = fib_trends[0]
                banner_text = f"**{selected_ticker} Main Trend {main_trend['type']}** {main_trend['f_start'].strftime('%Y-%m-%d')} - {main_trend['f_end'].strftime('%Y-%m-%d')} ({main_trend['move_pct']*100:.1f}%). {len(fib_trends)} trends detected."
                if main_trend['type'] == "Bullish":
                    st.success(f"🚀 {banner_text}")
                else:
                    st.info(f"🤖 {banner_text}")

            with top_layout_right:
                st.markdown(f"**Selected Asset:** `{selected_ticker}`")
                inspect_active = st.toggle("📈 Visualize Trends Overlay", value=True, key="fibo_trend_inspect")

            h = 0 if fib_hist.empty else fib_hist['High'].max()
            l = 0 if fib_hist.empty else fib_hist['Low'].min()
            d = h - l
            
            dynamic_fibs = {
                "0% (High)": h,
                "38.2% Retracement": h - 0.382 * d,
                "50.0% Center Line": h - 0.5 * d,
                "61.8% Golden Pocket": h - 0.618 * d,
                "100% (Low Base)": l
            }

            if inspect_active:
                chart_col, sidebar_col = st.columns([3, 1])
                with chart_col:
                    st.plotly_chart(create_chart(selected_ticker, fib_hist, dynamic_fibs, fib_trends, inspect_active), use_container_width=True)            
                
                with sidebar_col:
                    curr_p = pick['data']['🌐 Price']
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
                                💵 Live Dividend Yield: {pick["data"]["Div Yield"]:.0f}%
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
                    st.markdown("##### Fibonacci Levels")
                    st.caption(f"Range: {st.session_state['fib_start']} to {st.session_state['fib_end']}")
                    
                    for label, val in dynamic_fibs.items():
                        prox = abs(curr_p - val) / val * 100
                        prefix = "🎯" if prox < 1.5 else "⚪"
                        st.write(f"{prefix} **{label}:** {val:.2f}")
            else:
                st.plotly_chart(create_chart(selected_ticker, fib_hist, dynamic_fibs, fib_trends, inspect_active), use_container_width=True)
        else:
            st.error("No valid dataset targets matching context index queries.")