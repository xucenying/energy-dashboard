import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Energy Price Forecast Dashboard", layout="wide")

st.title("72‑Hour Energy Price Outlook (Pitch Demo)")
st.caption("Day-ahead prices / forecasts + cheapest operating window for flexible loads.")

uploaded = st.file_uploader("Upload CSV (timestamp, price_eur_mwh, optional load_fcst_mw, load_actual_mw)", type=["csv"])

@st.cache_data
def load_csv(f):
    df = pd.read_csv(f)
    if "timestamp" not in df.columns:
        raise ValueError("CSV must include a 'timestamp' column")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    return df

def cheapest_window(df, hours=4, col="price_eur_mwh"):
    s = df.set_index("timestamp")[col].dropna()
    # ensure hourly regularity is not required; rolling over rows
    roll = s.rolling(hours).mean()
    end = roll.idxmin()
    if pd.isna(end):
        return None
    start = end - pd.Timedelta(hours=hours)
    return start, end, float(roll.loc[end])

if uploaded:
    df = load_csv(uploaded)

    if "price_eur_mwh" not in df.columns:
        st.error("Missing column: price_eur_mwh")
        st.stop()

    # Controls
    st.sidebar.header("Controls")
    window_hours = st.sidebar.slider("Cheapest window length (hours)", 1, 12, 4)
    currency = st.sidebar.selectbox("Currency label", ["EUR/MWh", "€/MWh"], index=0)

    # Filter to next 72h from first timestamp in file (for demo)
    t0 = df["timestamp"].min()
    df72 = df[(df["timestamp"] >= t0) & (df["timestamp"] < t0 + pd.Timedelta(hours=72))].copy()

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours shown", len(df72))
    c2.metric("Avg price", f"{df72['price_eur_mwh'].mean():.2f} {currency}")
    c3.metric("Min price", f"{df72['price_eur_mwh'].min():.2f} {currency}")
    c4.metric("Max price", f"{df72['price_eur_mwh'].max():.2f} {currency}")

    # Cheapest window
    res = cheapest_window(df72, hours=window_hours, col="price_eur_mwh")
    if res:
        start, end, avgp = res
        st.success(f"Cheapest {window_hours}‑hour window: **{start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC** (avg **{avgp:.2f} {currency}**)")

    # Price chart with highlighted cheapest window
    fig = px.line(df72, x="timestamp", y="price_eur_mwh", title="Hourly price outlook (next 72h)")
    if res:
        fig.add_vrect(x0=start, x1=end, fillcolor="green", opacity=0.15, line_width=0)
    fig.update_yaxes(title=f"Price ({currency})")
    fig.update_xaxes(title="Time (UTC)")
    st.plotly_chart(fig, use_container_width=True)

    # Optional load section
    left, right = st.columns(2)
    with left:
        st.subheader("Load (optional)")
        load_cols = [c for c in ["load_fcst_mw", "load_actual_mw"] if c in df72.columns]
        if load_cols:
            fig2 = px.line(df72, x="timestamp", y=load_cols, title="Load forecast vs actual")
            fig2.update_yaxes(title="MW")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No load columns found. Add load_fcst_mw / load_actual_mw to show this panel.")

    with right:
        st.subheader("Recommendation (pitch text)")
        st.write(
            f"""
**Suggested action:** shift flexible consumption into the highlighted low-price window.

**Example:** EV depot charging / batch process scheduling  
- Avoid hours with high prices (peaks)  
- Prefer the cheapest {window_hours}-hour block  
- Keep operational constraints (deadline, max site kW)
"""
        )

    # Data preview
    with st.expander("Preview data"):
        st.dataframe(df72.head(50), use_container_width=True)

else:
    st.info("Upload a CSV to start. If you want, I can give you a sample CSV format.")