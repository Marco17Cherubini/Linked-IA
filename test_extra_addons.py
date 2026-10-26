import pandas as pd
import numpy as np
from extra_addons import (
    fetch_historical_batch, get_window, calc_extra_addons, 
    calc_all_extra_addons, fetch_historical_prices_perplexity,
    calc_addons_from_perplexity_data
)

print("=== TEST SISTEMA EXTRA ADDONS CON PERPLEXITY ===\n")

# Test 1: Download dati storici da yfinance
dates = ['2023-10-07']
tickers = {'SP500': '^GSPC', 'NASDAQ': '^IXIC'}
print("1. Download dati storici da yfinance...")
hist = fetch_historical_batch(dates, tickers, window=7)

print("\n2. Dati scaricati:")
for k, v in hist.items():
    if v is not None and not v.empty:
        print(f"  {k}: {len(v)} righe")
    else:
        print(f"  {k}: Nessun dato")

# Test 2: Estrai finestra
print("\n3. Estrai finestra 7 giorni...")
if 'SP500' in hist and hist['SP500'] is not None and not hist['SP500'].empty:
    window = get_window(hist['SP500'], '2023-10-07', window=7)
    print(f"  Finestra: {len(window)} giorni")
    if not window.empty:
        print(f"  Close values: {window['Close'].values}")
        
        # Test 3: Calcola extra addons
        print("\n4. Calcola extra addons (senza Perplexity)...")
        extra = calc_extra_addons(window)
        last = extra.iloc[-1]
        
        print(f"  rolling_min7: {last['rolling_min7']:.2f}" if not pd.isna(last['rolling_min7']) else "  rolling_min7: NaN")
        print(f"  rolling_max7: {last['rolling_max7']:.2f}" if not pd.isna(last['rolling_max7']) else "  rolling_max7: NaN")
        print(f"  zscore7: {last['zscore7']:.4f}" if not pd.isna(last['zscore7']) else "  zscore7: NaN (richiede min 2 valori)")
        print(f"  percentile7: {last['percentile7']:.4f}" if not pd.isna(last['percentile7']) else "  percentile7: NaN")
        print(f"  drawdown: {last['drawdown']:.4f}" if not pd.isna(last['drawdown']) else "  drawdown: NaN")
        print(f"  momentum7: {last['momentum7']:.2f}" if not pd.isna(last['momentum7']) else "  momentum7: NaN (richiede 7+ giorni)")
        print(f"  volatility7: {last['volatility7']:.6f}" if not pd.isna(last['volatility7']) else "  volatility7: NaN (richiede min 2 valori)")
else:
    print("  Dati SP500 non disponibili")

# Test 4: Test Perplexity API per dati storici
print("\n5. Test Perplexity API per recupero dati storici...")
perplexity_prices = fetch_historical_prices_perplexity('SP500', '2023-10-06', days_needed=14)
if perplexity_prices:
    print(f"  Perplexity ha restituito {len(perplexity_prices)} prezzi")
    print(f"  Primi 3: {perplexity_prices[:3]}")
    
    # Calcola add-ons dai dati Perplexity
    pplx_addons = calc_addons_from_perplexity_data(perplexity_prices, window=7)
    print(f"  momentum7 da Perplexity: {pplx_addons['momentum7']:.2f}" if not pd.isna(pplx_addons['momentum7']) else "  momentum7: NaN")
    print(f"  volatility7 da Perplexity: {pplx_addons['volatility7']:.6f}" if not pd.isna(pplx_addons['volatility7']) else "  volatility7: NaN")
else:
    print("  Perplexity non ha restituito dati (verifica API key)")

# Test 5: Calcola tutti gli extra addons con fallback Perplexity
print("\n6. Test calc_all_extra_addons CON fallback Perplexity...")
all_addons = calc_all_extra_addons('2023-10-06', window=7, use_perplexity_fallback=True)
print(f"  Totale add-ons calcolati: {len(all_addons)}")

# Conta valori validi vs NaN
valid_count = sum(1 for v in all_addons.values() if not pd.isna(v))
nan_count = sum(1 for v in all_addons.values() if pd.isna(v))
print(f"  Valori validi: {valid_count}")
print(f"  Valori NaN: {nan_count}")

# Mostra momentum7 e volatility7 per tutti gli indici
print("\n  Valori momentum7 e volatility7 per indice:")
for idx in ['SP500', 'NASDAQ', 'DAX', 'FTSE100', 'NIKKEI']:
    m = all_addons.get(f'{idx}_momentum7', np.nan)
    v = all_addons.get(f'{idx}_volatility7', np.nan)
    m_str = f"{m:.2f}" if not pd.isna(m) else "NaN"
    v_str = f"{v:.6f}" if not pd.isna(v) else "NaN"
    print(f"    {idx}: momentum7={m_str}, volatility7={v_str}")

print("\n✅ Test completato!")
