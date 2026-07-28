import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Chart-Analyzer", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;} h1{color:#00d4aa;}</style>", unsafe_allow_html=True)

st.title("📈 Chart-Analyzer")
st.write("Lade deine CSV-Dateien hoch und vergleiche sie :)(MT5, TradingView oder Capital.com).")

def lade(datei):
    inhalt = datei.getvalue().decode("utf-8")
    trenner = "\t" if "\t" in inhalt.split("\n")[0] else ","
    datei.seek(0)
    df = pd.read_csv(datei, sep=trenner)

    spalten = {}
    for name in df.columns:
        k = name.lower()
        for gesucht in ["open", "high", "low", "close"]:
            if gesucht in k and gesucht not in spalten:
                spalten[gesucht] = name

    zeit = None
    for name in df.columns:
        if ("date" in name.lower() or "time" in name.lower()) and zeit is None:
            zeit = name

    if zeit is not None:
        if pd.api.types.is_numeric_dtype(df[zeit]):
            df["Zeit"] = pd.to_datetime(df[zeit], unit="s", errors="coerce")
        else:
            df["Zeit"] = pd.to_datetime(df[zeit], errors="coerce")
    else:
        df["Zeit"] = pd.RangeIndex(len(df))
    return df, spalten

dateien = st.file_uploader("Dateien auswählen", type="csv", accept_multiple_files=True)

if dateien:
    sma_laenge = st.sidebar.slider("SMA-Länge", 10, 200, 50)
    typ = st.sidebar.radio("Chart-Typ", ["Linie", "Kerzen"])

    for datei in dateien:
        st.divider()
        st.subheader(datei.name)

        df, sp = lade(datei)
        if "close" not in sp:
            st.error("Keine Close-Spalte gefunden.")
            continue

        df = df.dropna(subset=["Zeit"])
        tage = df["Zeit"].dt.date
        von, bis = st.select_slider("Zeitraum",
                                    options=sorted(tage.unique()),
                                    value=(tage.min(), tage.max()),
                                    key=datei.name)
        df = df[(tage >= von) & (tage <= bis)]
        close = df[sp["close"]]

        if len(df) < 2:
            st.warning("Zu wenig Daten im Zeitraum.")
            continue

        veraenderung = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2)
        vola = round(close.pct_change().std() * 100, 3)

        a, b, c, d, e = st.columns(5)
        a.metric("Kerzen", len(df))
        b.metric("Veränderung", str(veraenderung) + " %")
        c.metric("Höchster", round(close.max(), 4))
        d.metric("Tiefster", round(close.min(), 4))
        e.metric("Volatilität", str(vola) + " %")

        chart_df = df
        if len(df) > 5000:
            schritt = len(df) // 5000
            chart_df = df.iloc[::schritt]
            st.warning("Zu viele Kerzen – Chart zeigt nur jede " + str(schritt) + ". Kerze. Für alle Details den Zeitraum enger stellen.")

        fig = go.Figure()
        if typ == "Kerzen" and "open" in sp and "high" in sp and "low" in sp:
            fig.add_trace(go.Candlestick(x=chart_df["Zeit"], open=chart_df[sp["open"]],
                                         high=chart_df[sp["high"]], low=chart_df[sp["low"]],
                                         close=chart_df[sp["close"]], name="Kurs"))
        else:
            fig.add_trace(go.Scatter(x=chart_df["Zeit"], y=chart_df[sp["close"]], name="Preis",
                                     line=dict(color="#00d4aa", width=1)))

        fig.add_trace(go.Scatter(x=chart_df["Zeit"], y=chart_df[sp["close"]].rolling(sma_laenge).mean(),
                                 name="SMA" + str(sma_laenge), line=dict(color="#ff9f43", width=2)))
        fig.update_layout(template="plotly_dark", height=550, hovermode="x unified",
                          xaxis_rangeslider_visible=False,
                          xaxis=dict(tickformat="%d.%m.%Y\n%H:%M", showgrid=True))
        st.plotly_chart(fig, use_container_width=True)

        st.download_button("CSV herunterladen", df.to_csv(index=False), datei.name)
