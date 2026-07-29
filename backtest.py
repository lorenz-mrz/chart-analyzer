import pandas as pd

df = pd.read_csv("XAUUSD_H1_202001020600_202607272000.csv", sep="\t")
close = df["<CLOSE>"]
sma = close.rolling(50).mean()

drueber = close > sma
signal = drueber & ~drueber.shift(1, fill_value=False)

print("Kerzen:", len(df))
print("Kaufsignale:", signal.sum())
zukunft = close.shift(-100)
ergebnis = (zukunft - close) / close * 100

treffer = ergebnis[signal]

print("Trades:", len(treffer.dropna()))
print("Ø Ergebnis:", round(treffer.mean(), 3), "%")
print("Winrate:", round((treffer > 0).mean() * 100, 1), "%")
import matplotlib.pyplot as plt


equity = treffer.dropna().cumsum()
equity.plot(title="Equity-Kurve (kumuliert in %)")
plt.show()
kaufen_halten = (close.iloc[-1] / close.iloc[0] - 1) * 100
strategie = treffer.dropna().sum()


print("")
print("--- Vergleich ---")
print("Buy & Hold:", round(kaufen_halten, 1), "%")
print("Strategie:", round(strategie, 1), "%")
print("")
print("--- Ehrlicher Backtest (ein Trade gleichzeitig) ---")


haltedauer = 100
trades = []
i = 0
while i < len(close) - haltedauer:
    if signal.iloc[i]:
        einstieg = close.iloc[i]
        ausstieg = close.iloc[i + haltedauer]
        trades.append((ausstieg - einstieg) / einstieg * 100)
        i = i + haltedauer
    else:
        i = i + 1


trades = pd.Series(trades)
print("Trades:", len(trades))
print("Winrate:", round((trades > 0).mean() * 100, 1), "%")
print("Gesamt:", round(trades.sum(), 1), "%")
print("")
print("--- Mit Stop & Ziel (R-Multiples) ---")


high = df["<HIGH>"]
low = df["<LOW>"]
stop_prozent = 1.0
ziel_r = 2.0


r_ergebnisse = []
i = 0
while i < len(close) -1:
    if signal.iloc[i]:
        entry = close.iloc[i]
        stop = entry * (1 - stop_prozent / 100)
        ziel = entry + (entry - stop) * ziel_r


        j = i + 1
        while j < len(close):
            if low.iloc[j] <= stop:
                r_ergebnisse.append(-1.0)
                break
            if high.iloc[j] >= ziel:
                r_ergebnisse.append(ziel_r)
                break
            j = j + 1
        i = j + 1
    else:
        i = i + 1


r = pd.Series(r_ergebnisse)
print("Trades:", len(r))
print("Winrate:", round((r > 0).mean() * 100, 1), "%")
print("Gesamt:", round(r.sum(), 1), "R")
print("Erwartung/Trade:", round(r.mean(), 3), "R")
print("")
print("--- GEGENTEST: Short-Regel ---")

signal_short = (~drueber) & drueber.shift(1, fill_value=False)

r_short = []
i = 0
while i < len(close) - 1:
    if signal_short.iloc[i]:
        entry = close.iloc[i]
        stop = entry * (1 + stop_prozent / 100)
        ziel = entry - (stop - entry) * ziel_r
        j = i + 1
        while j < len(close):
            if high.iloc[j] >= stop:
                r_short.append(-1.0)
                break
            if low.iloc[j] <= ziel:
                r_short.append(ziel_r)
                break
            j = j + 1
        i = j + 1
    else:
        i = i + 1

rs = pd.Series(r_short)
print("Trades:", len(rs))
print("Winrate:", round((rs > 0).mean() * 100, 1), "%")
print("Gesamt:", round(rs.sum(), 1), "R")
   
