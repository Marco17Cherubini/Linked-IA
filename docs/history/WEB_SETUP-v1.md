# LinkedIA - Web Frontend Setup Guide

## 🎨 Interfacce Web Create

Hai a disposizione **DUE** frontend completi:

### 1. **React Frontend** (Raccomandato)
- Directory: `frontend-react/`
- Tecnologie: React 18 + Vite + TailwindCSS
- Porta: 3000

### 2. **Vue Frontend** (Alternativa)
- Directory: `frontend-vue/`
- Tecnologie: Vue 3 + Vite + TailwindCSS  
- Porta: 3001

Entrambi includono:
- 🏠 Home page con overview
- 🔍 Pagina analisi con form data
- 📜 Storico analisi
- 📊 Statistiche sistema

---

## 🚀 Setup Rapido

### Prerequisiti

```powershell
# Verifica Node.js installato (richiesto 16+)
node --version

# Se non installato, scarica da: https://nodejs.org/
```

---

## 📦 Installazione

### Opzione 1: Frontend React

```powershell
# 1. Vai nella directory React
cd frontend-react

# 2. Installa dipendenze
npm install

# 3. Avvia in modalità sviluppo
npm run dev

# Frontend disponibile su: http://localhost:3000
```

### Opzione 2: Frontend Vue

```powershell
# 1. Vai nella directory Vue
cd frontend-vue

# 2. Installa dipendenze
npm install

# 3. Avvia in modalità sviluppo
npm run dev

# Frontend disponibile su: http://localhost:3001
```

---

## 🔧 Avvio Completo del Sistema

### Passo 1: Avvia il Backend API

In un terminale PowerShell:

```powershell
# Torna alla directory principale
cd c:\Users\marco\OneDrive\Desktop\Marco\UNIUPO\Laurea\LinkedIA

# Installa flask-cors se non presente
pip install flask-cors

# Avvia il server API
python api_server.py

# Backend API disponibile su: http://localhost:5000
```

### Passo 2: Avvia il Frontend (React O Vue)

In un **NUOVO** terminale PowerShell:

**Per React:**
```powershell
cd c:\Users\marco\OneDrive\Desktop\Marco\UNIUPO\Laurea\LinkedIA\frontend-react
npm run dev
```

**Per Vue:**
```powershell
cd c:\Users\marco\OneDrive\Desktop\Marco\UNIUPO\Laurea\LinkedIA\frontend-vue
npm run dev
```

### Passo 3: Apri nel Browser

- **React**: http://localhost:3000
- **Vue**: http://localhost:3001

---

## 🎯 Utilizzo dell'Interfaccia Web

### 1. Home Page
- Overview del sistema
- Statistiche generali
- Accesso rapido all'analisi

### 2. Pagina Analisi
1. Inserisci una data (es: `2022-02-24`)
2. Clicca "Analizza"
3. Attendi l'elaborazione (può richiedere 1-3 minuti)
4. Visualizza:
   - Articoli trovati
   - Prezzi di mercato
   - Indicatori tecnici
   - Report nessi
   - Sentenza LiA finale

### 3. Storico
- Vedi tutte le analisi passate
- Cerca per data
- Espandi dettagli

### 4. Statistiche
- Totale articoli analizzati
- Date coperte
- Indici monitorati

---

## 📡 API Endpoints Disponibili

Il backend Flask espone i seguenti endpoint:

### GET `/api/health`
Verifica stato server
```json
{
  "status": "ok",
  "message": "LinkedIA API is running"
}
```

### POST `/api/analyze`
Esegui analisi per una data
```json
{
  "date": "2022-02-24"
}
```

### GET `/api/history`
Ottieni storico analisi
```json
{
  "success": true,
  "history": [...]
}
```

### GET `/api/article/:date`
Dettagli articolo per data specifica

### GET `/api/stats`
Statistiche generali del sistema

---

## 🛠️ Build per Produzione

### React

```powershell
cd frontend-react
npm run build

# Crea cartella build/ con file ottimizzati
# Serviti tramite api_server.py (già configurato)
```

### Vue

```powershell
cd frontend-vue
npm run build

# Crea cartella dist/ con file ottimizzati
```

---

## 🔍 Troubleshooting

### Problema: "Cannot find module"
```powershell
# Reinstalla dipendenze
rm -r node_modules
npm install
```

### Problema: "Port already in use"
```powershell
# Cambia porta in vite.config.js
server: {
  port: 3002  # Usa porta diversa
}
```

### Problema: "CORS Error"
```powershell
# Verifica che flask-cors sia installato
pip install flask-cors

# Verifica che api_server.py abbia CORS abilitato
```

### Problema: API non risponde
```powershell
# Verifica backend in esecuzione
# Terminal 1: python api_server.py
# Terminal 2: npm run dev

# Test API direttamente:
curl http://localhost:5000/api/health
```

---

## 📂 Struttura File

```
LinkedIA/
├── api_server.py              # Backend Flask con REST API
│
├── frontend-react/            # Frontend React
│   ├── src/
│   │   ├── App.jsx           # App principale
│   │   ├── main.jsx          # Entry point
│   │   ├── index.css         # Stili globali
│   │   └── components/
│   │       ├── HomePage.jsx
│   │       ├── AnalysisPage.jsx
│   │       ├── HistoryPage.jsx
│   │       └── StatsPage.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
└── frontend-vue/              # Frontend Vue (alternativa)
    ├── src/
    │   ├── App.vue
    │   ├── main.js
    │   ├── style.css
    │   └── components/
    │       ├── HomePage.vue
    │       ├── AnalysisPage.vue
    │       ├── HistoryPage.vue
    │       ├── StatsPage.vue
    │       ├── ArticleCard.vue
    │       ├── HistoryItem.vue
    │       ├── FeatureCard.vue
    │       ├── StatCard.vue
    │       └── StepItem.vue
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

---

## 🎨 Personalizzazione

### Cambiare Colori

**React/Vue - tailwind.config.js:**
```javascript
theme: {
  extend: {
    colors: {
      primary: '#2563eb',    // Blu
      secondary: '#fbbf24',  // Giallo
    }
  }
}
```

### Modificare Stili

**React - src/index.css**  
**Vue - src/style.css**

```css
/* Cambia gradiente sfondo */
body {
  background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
}
```

---

## 🚦 Comandi Utili

```powershell
# Backend
python api_server.py              # Avvia API server

# React
cd frontend-react
npm install                       # Installa dipendenze
npm run dev                       # Sviluppo
npm run build                     # Build produzione
npm run preview                   # Preview build

# Vue
cd frontend-vue
npm install                       # Installa dipendenze
npm run dev                       # Sviluppo
npm run build                     # Build produzione
```

---

## ✅ Checklist Finale

- [ ] Backend API in esecuzione (port 5000)
- [ ] Frontend in esecuzione (port 3000 o 3001)
- [ ] Flask-cors installato
- [ ] Node.js 16+ installato
- [ ] Chiave OpenAI configurata
- [ ] Database directory creata
- [ ] Browser aperto su localhost

---

## 🎓 Note Importanti

1. **CORS**: Il backend usa flask-cors per permettere chiamate dal frontend
2. **Proxy**: Vite è configurato per proxy delle richieste `/api` al backend
3. **Hot Reload**: Entrambi i frontend supportano hot reload (modifiche in tempo reale)
4. **Compatibilità**: Testato su Chrome, Firefox, Edge

---

## 📧 Supporto

Per problemi con l'interfaccia web:
1. Verifica console browser (F12)
2. Controlla terminal backend per errori API
3. Verifica network tab per chiamate fallite
4. Riavvia backend e frontend

---

**Buon lavoro con LinkedIA! 🚀📊**
