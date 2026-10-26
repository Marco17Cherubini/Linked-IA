"""
LinkedIA Configuration Utility
Helps manage API keys and environment setup safely
"""
import os
from pathlib import Path

def setup_environment():
    """Interactive setup for LinkedIA environment"""
    print("=" * 60)
    print("LinkedIA - Setup Wizard")
    print("=" * 60)
    
    # Check if .env exists
    env_path = Path(".env")
    if env_path.exists():
        print("\n✓ File .env già esistente")
        overwrite = input("Vuoi sovrascriverlo? (s/n): ").lower()
        if overwrite != 's':
            print("Setup annullato.")
            return
    
    # Get OpenAI API Key
    print("\n" + "─" * 60)
    print("CONFIGURAZIONE CHIAVE OPENAI")
    print("─" * 60)
    print("Puoi trovare la tua chiave API su: https://platform.openai.com/api-keys")
    api_key = input("\nInserisci la tua chiave OpenAI API: ").strip()
    
    if not api_key.startswith("sk-"):
        print("  Attenzione: la chiave non sembra valida (dovrebbe iniziare con 'sk-')")
        proceed = input("Vuoi continuare comunque? (s/n): ").lower()
        if proceed != 's':
            print("Setup annullato.")
            return
    
    # Write .env file
    with open(".env", "w") as f:
        f.write("# LinkedIA Environment Variables\n")
        f.write(f"OPENAI_API_KEY={api_key}\n")
        f.write("\n# Database Settings\n")
        f.write("DATABASE_PATH=./database/database.xlsx\n")
        f.write("\n# Market Data Settings\n")
        f.write("DEFAULT_MARKET_CALENDAR=XNYS\n")
        f.write("TRADING_WINDOW_DAYS=20\n")
        f.write("\n# Analysis Settings\n")
        f.write("SIMILARITY_THRESHOLD=0.0\n")
        f.write("MAX_HISTORICAL_DAYS=15\n")
    
    print("\n" + "=" * 60)
    print("✓ Setup completato!")
    print("=" * 60)
    print("\nFile .env creato con successo.")
    print("\n  IMPORTANTE: Ora devi modificare i file Python per usare la variabile d'ambiente:")
    print("    Sostituisci in archive_manager.py, analizer2.py, LiA.py:")
    print("    openai.api_key = (\"sk-proj-...\")")
    print("    con:")
    print("    import os")
    print("    from dotenv import load_dotenv")
    print("    load_dotenv()")
    print("    openai.api_key = os.getenv('OPENAI_API_KEY')")
    print("\nPer iniziare, esegui: python main.py")

def check_dependencies():
    """Check if all required packages are installed"""
    print("\n" + "=" * 60)
    print("CONTROLLO DIPENDENZE")
    print("=" * 60)
    
    required = [
        "pandas", "numpy", "openpyxl", "yfinance", 
        "pandas_market_calendars", "scikit-learn", "openai",
        "feedparser", "beautifulsoup4", "requests", "flask"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MANCANTE")
            missing.append(package)
    
    if missing:
        print("\n  Pacchetti mancanti rilevati!")
        print(f"Installa con: pip install {' '.join(missing)}")
    else:
        print("\n✓ Tutte le dipendenze sono installate!")
    
    return len(missing) == 0

if __name__ == "__main__":
    print("\nLinkedIA - Linked Intelligent Analyst")
    print("Setup & Configuration Tool\n")
    
    choice = input("Cosa vuoi fare?\n1. Setup ambiente (.env)\n2. Controlla dipendenze\n3. Entrambi\n\nScelta (1/2/3): ").strip()
    
    if choice in ["1", "3"]:
        setup_environment()
    
    if choice in ["2", "3"]:
        check_dependencies()
    
    print("\nSetup completato. Premi Enter per uscire...")
    input()
