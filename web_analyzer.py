import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Chart-Analyzer", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;} h1{color:#00d4aa;}</style>", unsafe_allow_html=True)

st.title("📈 Chart-Analyzer")
st.write("Lade CSV-Dateien hoch (MT5, TradingView oder Capital.com).")

def lade(datei):
    inhalt = datei.getvalue().decode("utf-8")
    trenner = "\t" if "\t" in inhalt.split("\n")[0] else ","
    datei.seek(0)
    df = pd.read_csv(datei, sep=trenner)
    spalten = {}
    for name in df.columns:
        k = name.lower()
        for g in ["open", "high", "low", "close"]:
            if g in k and g not in spalten:
                spalten[g] = name
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

def backtest(close, high, low, signal, stop_prozent, ziel_r, richtung):
    ergebnisse = []
    i = 0
    while i < len(close) - 1:
        if signal.iloc[i]:
            entry = close.iloc[i]
            if richtung == "Long":
                stop = entry * (1 - stop_prozent / 100)
                ziel = entry + (entry - stop) * ziel_r
            else:
                stop = entry * (1 + stop_prozent / 100)
                ziel = entry - (stop - entry) * ziel_r
            j = i + 1
            while j < len(close):
                if richtung == "Long":
                    raus_stop = low.iloc[j] <= stop
                    raus_ziel = high.iloc[j] >= ziel
                else:
                    raus_stop = high.iloc[j] >= stop
                    raus_ziel = low.iloc[j] <= ziel
                if raus_stop:
                    ergebnisse.append(-1.0)
                    break
                if raus_ziel:
                    ergebnisse.append(ziel_r)
                    break
                j = j + 1
            i = j + 1
        else:
            i = i + 1
    return pd.Series(ergebnisse)

dateien = st.file_uploader("Dateien auswählen", type="csv", accept_multiple_files=True)

if dateien:
    sma_laenge = st.sidebar.slider("SMA-Länge", 10, 200, 50)
    typ = st.sidebar.radio("Chart-Typ", ["Linie", "Kerzen"])
    st.sidebar.divider()
    bt_an = st.sidebar.checkbox("Backtest anzeigen")
    stop_prozent = st.sidebar.number_input("Stop in %", 0.1, 10.0, 1.0, 0.1)
    ziel_r = st.sidebar.number_input("Ziel in R", 1.0, 10.0, 2.0, 0.5)

    for datei in dateien:
        st.divider()
        st.subheader(datei.name)
        df, sp = lade(datei)
        if "close" not in sp:
            st.error("Keine Close-Spalte gefunden.")
            continue

        df = df.dropna(subset=["Zeit"])
        tage = df["Zeit"].dt.date
        von, bis = st.select_slider("Zeitraum", options=sorted(tage.unique()),
                                    value=(tage.min(), tage.max()), key=datei.name)
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
            st.warning("Chart zeigt nur jede " + str(schritt) + ". Kerze. Für Details Zeitraum enger stellen.")

        fig = go.Figure()
        if typ == "Kerzen" and "open" in sp:
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

        if bt_an and "high" in sp and "low" in sp:
            st.markdown("### 🎯 Backtest: SMA-Kreuzung")
            sma = close.rolling(sma_laenge).mean()
            drueber = close > sma
            sig_long = drueber & ~drueber.shift(1, fill_value=False)
            sig_short = (~drueber) & drueber.shift(1, fill_value=False)
            high = df[sp["high"]]
            low = df[sp["low"]]

            r_long = backtest(close, high, low, sig_long, stop_prozent, ziel_r, "Long")
            r_short = backtest(close, high, low, sig_short, stop_prozent, ziel_r, "Short")

            bh = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 1)
            breakeven = round(100 / (1 + ziel_r), 1)

            k1, k2 = st.columns(2)
            with k1:
                st.write("**Long**")
                st.write("Trades:", len(r_long))
                st.write("Winrate:", round((r_long > 0).mean() * 100, 1), "%")
                st.write("Gesamt:", round(r_long.sum(), 1), "R")
            with k2:
                st.write("**Short (Gegentest)**")
                st.write("Trades:", len(r_short))
                st.write("Winrate:", round((r_short > 0).mean() * 100, 1), "%")
                st.write("Gesamt:", round(r_short.sum(), 1), "R")

            st.caption("Break-even-Winrate bei " + str(ziel_r) + "R: " + str(breakeven) + " %  ·  Buy & Hold: " + str(bh) + " %")

            if len(r_long) > 0 and len(r_short) > 0:
                if r_long.sum() > 0 and r_short.sum() < 0:
                    st.warning("⚠️ Long gewinnt, Short verliert → wahrscheinlich nur Markttrend (Beta), kein echter Edge.")

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(y=r_long.cumsum(), name="Long", line=dict(color="#00d4aa")))
            fig2.add_trace(go.Scatter(y=r_short.cumsum(), name="Short", line=dict(color="#ff5252")))
            fig2.update_layout(template="plotly_dark", height=350, title="Equity-Kurven (in R)")
            st.plotly_chart(fig2, use_container_width=True)

        st.download_button("CSV herunterladen", df.to_csv(index=False), datei.name)
