# 0004 — Un solo frontend React con Recharts

**Stato**: accettata (ottobre 2026)

**Contesto.** Esistevano un frontend React e uno Vue con le stesse quattro schermate, più una pagina HTML statica. Le dipendenze installate erano incomplete e nessuna build funzionava.

**Decisione.** Un solo frontend React (Vite, React Router) riprogettato da zero, con stile proprio basato su token CSS (tema chiaro e scuro) e Recharts 3 come unica libreria grafica. Alternative valutate: visx (troppo codice proprio), ECharts e Plotly (bundle pesante, canvas meno accessibile), Lightweight Charts (non copre istogrammi e grafici a punti). La 2.x di Recharts è dichiarata non più mantenuta.

**Conseguenze.** Il blocco dei grafici pesa circa 165 kB compressi ed è caricato solo dalle pagine che lo usano. Ogni grafico ha riepilogo testuale e tabella dati come alternativa accessibile.
