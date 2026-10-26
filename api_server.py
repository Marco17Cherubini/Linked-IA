"""
LinkedIA - Flask Backend API
Provides REST endpoints for the LinkedIA frontend
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from datetime import datetime
import pandas as pd
import traceback

# Import LinkedIA modules
from fetcher import fetch_rss_news
from scraper import scrape_articles
from new_store_articles2 import store_articles
from archive_manager import selezione_intelligente
from deepseek_manager import run_lia_deepseek, run_analysis_deepseek  # DeepSeek per analisi pattern
from db_manager import crea_database_se_necessario, get_database_dir

app = Flask(__name__, static_folder='frontend-react/build', static_url_path='')
CORS(app, origins=["http://localhost:3000"], resources={r"/api/*": {"origins": "http://localhost:3000"}})

@app.route('/api/test', methods=['GET'])
def test_connection():
    """Test endpoint per verificare connessione frontend-backend"""
    return jsonify({
        'status': 'connected',
        'message': 'Frontend e Backend sono collegati!',
        'timestamp': datetime.now().isoformat(),
        'server': 'Flask on port 5000'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if API is running"""
    return jsonify({
        'status': 'ok',
        'message': 'LinkedIA API is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Main analysis endpoint
    Expects: { "date": "YYYY-MM-DD" }
    Returns: Analysis results
    """
    print(f"\\n[API] Richiesta analisi ricevuta...")
    try:
        data = request.get_json()
        print(f"[API] Data ricevuta: {data}")
        date_filter = data.get('date')
        
        if not date_filter:
            return jsonify({'error': 'Date parameter is required'}), 400
        
        print(f"[API] Avvio analisi per data: {date_filter}")
        
        # Validate date format
        try:
            datetime.strptime(date_filter, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Step 1: Fetch news from RSS
        print(f"[API] Step 1: Fetch RSS news...")
        df_links = fetch_rss_news({
            "Reuters": "https://feeds.reuters.com/reuters/topNews",
            "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "Investing": "https://www.investing.com/rss/news_25.rss"
        }, date_filter)
        
        articoli_completi = []
        
        if not df_links.empty:
            print(f"[API] RSS: trovati {len(df_links)} link")
            # News found in RSS feeds
            dettagli = scrape_articles(df_links)
            if len(dettagli) > 0:
                store_articles(dettagli)
                # Get stored articles with prices
                xlsx_path = crea_database_se_necessario()
                df_db = pd.read_excel(xlsx_path)
                df_filtered = df_db[df_db['Data'] == date_filter]
                
                for _, row in df_filtered.iterrows():
                    articoli_completi.append({
                        'Titolo': row.get('Titolo', ''),
                        'Corpo': row.get('Corpo', ''),
                        'Fonti': row.get('Fonti', ''),
                        'Data': row.get('Data', ''),
                        'prezzi': {k: v for k, v in row.items() if 'Close' in k or 'Open' in k},
                        'addons': {k: v for k, v in row.items() if any(x in k for x in ['gap_ret', 'atr7', 'rv7'])}
                    })
        else:
            # Use intelligent selection (Perplexity)
            print(f"[API] RSS vuoto, uso selezione intelligente Perplexity...")
            articoli = selezione_intelligente(date_filter)
            print(f"[API] Perplexity: trovati {len(articoli) if articoli else 0} articoli")
            if articoli:
                # Converti articoli Perplexity nel formato per store_articles
                dettagli_perplexity = []
                for articolo in articoli:
                    if articolo.get('fonti'):
                        dettagli_perplexity.append({
                            'Titolo': articolo['titolo'],
                            'Corpo': articolo.get('corpo', ''),
                            'Fonti': '; '.join(articolo['fonti']) if isinstance(articolo['fonti'], list) else articolo['fonti'],
                            'Data': articolo['data']
                        })
                
                # Passa attraverso store_articles per recuperare prezzi e addons
                if dettagli_perplexity:
                    print(f"[API] Recupero prezzi di mercato per {len(dettagli_perplexity)} articoli...")
                    store_articles(dettagli_perplexity)
                    
                    # Leggi dal database con prezzi e addons
                    xlsx_path = crea_database_se_necessario()
                    df_db = pd.read_excel(xlsx_path)
                    
                    # Cerca articoli per le date trovate
                    for art in dettagli_perplexity:
                        art_date = art['Data']
                        df_filtered = df_db[df_db['Data'] == art_date]
                        
                        if not df_filtered.empty:
                            row = df_filtered.iloc[-1]  # Prendi l'ultimo (più recente)
                            articoli_completi.append({
                                'Titolo': row.get('Titolo', art['Titolo']),
                                'Corpo': row.get('Corpo', art['Corpo']),
                                'Fonti': row.get('Fonti', art['Fonti']),
                                'Data': row.get('Data', art_date),
                                'prezzi': {k: v for k, v in row.items() if any(x in str(k) for x in ['Close', 'Open', 'High', 'Low', 'Volume']) and pd.notna(v)},
                                'addons': {k: v for k, v in row.items() if any(x in str(k) for x in ['gap_ret', 'intra_ret', 'atr7', 'rv7', 'zscore', 'momentum']) and pd.notna(v)}
                            })
                        else:
                            # Nessun dato nel DB, usa articolo grezzo
                            articoli_completi.append({
                                'Titolo': art['Titolo'],
                                'Corpo': art['Corpo'],
                                'Fonti': art['Fonti'],
                                'Data': art_date,
                                'prezzi': {},
                                'addons': {}
                            })
        
        print(f"[API] Step 2: Analisi DeepSeek su {len(articoli_completi)} articoli...")
        # Step 2: Run incremental analysis with DeepSeek
        report_nesso_list = []
        if articoli_completi:
            report_nesso_list = run_analysis_deepseek(articoli_completi)
        
        print(f"[API] Step 3: LiA pattern matching...")
        # Step 3: Run LiA DeepSeek final analysis
        lia_result = None
        if report_nesso_list:
            lia_result = run_lia_deepseek(report_nesso_list)
        
        print(f"[API] Analisi completata!")
        return jsonify({
            'success': True,
            'date': date_filter,
            'articles_found': len(articoli_completi),
            'articles': articoli_completi,
            'analysis': report_nesso_list,
            'lia_prediction': lia_result
        })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in analyze endpoint: {error_trace}")
        return jsonify({
            'error': str(e),
            'trace': error_trace
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get analysis history from database"""
    try:
        xlsx_path = crea_database_se_necessario()
        df = pd.read_excel(xlsx_path)
        
        # Get unique dates with article count
        history = df.groupby('Data').agg({
            'Titolo': 'count',
            'report_nesso': lambda x: x.notna().sum()
        }).reset_index()
        
        history.columns = ['date', 'article_count', 'analyzed_count']
        history = history.sort_values('date', ascending=False)
        
        return jsonify({
            'success': True,
            'history': history.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/article/<date>', methods=['GET'])
def get_article(date):
    """Get specific article details by date"""
    try:
        xlsx_path = crea_database_se_necessario()
        df = pd.read_excel(xlsx_path)
        df_filtered = df[df['Data'] == date]
        
        if df_filtered.empty:
            return jsonify({'error': 'No articles found for this date'}), 404
        
        articles = []
        for _, row in df_filtered.iterrows():
            articles.append({
                'date': row['Data'],
                'title': row['Titolo'],
                'body': row['Corpo'],
                'sources': row['Fonti'],
                'report_nesso': row.get('report_nesso', ''),
                'prices': {k: v for k, v in row.items() if any(x in k for x in ['Open', 'High', 'Low', 'Close', 'Volume'])},
                'addons': {k: v for k, v in row.items() if any(x in k for x in ['gap_ret', 'intra_ret', 'atr7', 'rv7', 'momentum', 'zscore'])}
            })
        
        return jsonify({
            'success': True,
            'articles': articles
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        xlsx_path = crea_database_se_necessario()
        df = pd.read_excel(xlsx_path)
        
        stats = {
            'total_articles': len(df),
            'total_dates': df['Data'].nunique(),
            'analyzed_articles': df['report_nesso'].notna().sum(),
            'date_range': {
                'earliest': df['Data'].min() if not df.empty else None,
                'latest': df['Data'].max() if not df.empty else None
            },
            'indices_tracked': ['SP500', 'NASDAQ', 'DAX', 'FTSE100', 'NIKKEI']
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print("=" * 70)
    print("LinkedIA Backend API Starting...".center(70))
    print("=" * 70)
    print("\nEndpoints available:")
    print("  GET  /api/health      - Health check")
    print("  POST /api/analyze     - Run analysis for a date")
    print("  GET  /api/history     - Get analysis history")
    print("  GET  /api/article/:date - Get article by date")
    print("  GET  /api/stats       - Get statistics")
    print("\nServer running on: http://localhost:5000")
    print("=" * 70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
