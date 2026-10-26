import numpy as np # consente il lavoro con array e funzioni matematiche
import pandas as pd # consente il lavoro con DataFrame

# Configurazione indici
INDICI = ["SP500", "NASDAQ", "DAX", "FTSE100", "NIKKEI"]

def calc_gap_ret(row, open_col, close_prev_col):
    try:
        if row[open_col] is not None and row[close_prev_col] not in (None, 0):
            return (float(row[open_col]) - float(row[close_prev_col])) / float(row[close_prev_col])
    except Exception:
        pass
    return None

def calc_intra_ret(row, open_col, close_col):
    try:
        if row[open_col] not in (None, 0) and row[close_col] is not None:
            return (float(row[close_col]) - float(row[open_col])) / float(row[open_col])
    except Exception:
        pass
    return None

def calc_range_pct(row, high_col, low_col, close_prev_col):
    try:
        if row[high_col] is not None and row[low_col] is not None and row[close_prev_col] not in (None, 0):
            return (float(row[high_col]) - float(row[low_col])) / float(row[close_prev_col])
    except Exception:
        pass
    return None

def calc_tr(row, high_col, low_col, close_prev_col):
    try:
        return max(
            float(row[high_col]) - float(row[low_col]),
            abs(float(row[high_col]) - float(row[close_prev_col])),
            abs(float(row[low_col]) - float(row[close_prev_col]))
        )
    except Exception:
        return None

def calc_atr7(df, idx, high_col, low_col, close_prev_col):
    try:
        window7 = df.iloc[max(0, idx-6):idx+1]
        tr_list = []
        for _, r in window7.iterrows():
            try:
                tr_val = max(
                    float(r[high_col]) - float(r[low_col]),
                    abs(float(r[high_col]) - float(r[close_prev_col])),
                    abs(float(r[low_col]) - float(r[close_prev_col]))
                )
                tr_list.append(tr_val)
            except:
                pass
        return np.mean(tr_list) if tr_list else None
    except Exception:
        return None

def calc_rv7(df, idx, close_col):
    try:
        window7 = df.iloc[max(0, idx-6):idx+1]
        close_vals = window7[close_col].astype(float).values
        returns = np.diff(close_vals) / close_vals[:-1]
        return np.sqrt(np.sum(returns**2)) if len(returns) > 0 else None
    except Exception:
        return None

def calc_rs_vol7(df, idx, high_col, low_col, open_col, close_col):
    try:
        window7 = df.iloc[max(0, idx-6):idx+1]
        rs_list = []
        for _, r in window7.iterrows():
            try:
                rs = np.log(float(r[high_col])/float(r[close_col])) * np.log(float(r[high_col])/float(r[open_col])) + \
                     np.log(float(r[low_col])/float(r[close_col])) * np.log(float(r[low_col])/float(r[open_col]))
                rs_list.append(rs)
            except:
                pass
        return np.mean(rs_list) if rs_list else None
    except Exception:
        return None

def calc_core_addons_from_row(row, df=None, idx=None): # le funzioni sopra definite si occupano di calcolare gli add-ons sotto definiti
    res = {}
    for index in INDICI:
        open_col = f"{index}_Open"
        close_col = f"{index}_Close"
        high_col = f"{index}_High"
        low_col = f"{index}_Low"
        volume_col = f"{index}_Volume"
        close_prev_col = f"{index}_Close_prev"
        # 1. Gap Return
        res[f"{index}_gap_ret"] = calc_gap_ret(row, open_col, close_prev_col)
        # 2. Intraday Return
        res[f"{index}_intra_ret"] = calc_intra_ret(row, open_col, close_col)
        # 3. Range %
        res[f"{index}_range_pct"] = calc_range_pct(row, high_col, low_col, close_prev_col)
        # 4. True Range
        res[f"{index}_tr"] = calc_tr(row, high_col, low_col, close_prev_col)
        # 5. ATR(7)
        res[f"{index}_atr7"] = calc_atr7(df, idx, high_col, low_col, close_prev_col) if df is not None and idx is not None else None
        # 6. Realized Volatility (RV, 7d)
        res[f"{index}_rv7"] = calc_rv7(df, idx, close_col) if df is not None and idx is not None else None
        # 7. Rogers–Satchell Vol (RS, 7d)
        res[f"{index}_rs_vol7"] = calc_rs_vol7(df, idx, high_col, low_col, open_col, close_col) if df is not None and idx is not None else None
    return res
def calc_core_addons_from_df(df): # applica calc_core_addons_from_row a ogni riga del DataFrame df e aggiunge le colonne degli add-ons core
    """
    Applica calc_core_addons_from_row a ogni riga del DataFrame df e aggiunge le colonne degli add-ons core.
    """
    df = df.copy()
    results = [calc_core_addons_from_row(row, df, idx) for idx, row in df.iterrows()]
    # Unisci i risultati come DataFrame
    addons_df = pd.DataFrame(results, index=df.index)
    # Aggiungi le colonne al DataFrame originale
    for col in addons_df.columns:
        df[col] = addons_df[col]
    return df

# Le funzioni sopra definite si occupano di calcolare i core add-ons sotto definiti (dal primo al sesto add on, numeri che pongono in relazioni tra loro i prezzi di più giorni, fondamentali per capire come reagisce il mercato sulla base della geopolitica e delle notizie economiche). Questi add-ons sono calcolati per ogni indice principale (SP500, NASDAQ, DAX, FTSE100, NIKKEI) e includono:
# Gli add-ons risultano fondamentali per stabilire i nessi tra la semantica (delle notizie) e il numerico (dei prezzi)