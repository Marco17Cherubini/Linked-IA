"""
LinkedIA - Quick Start Script
Run this to start the system with basic checks
"""
import sys
import os
from pathlib import Path

def print_header():
    print("\n" + "=" * 70)
    print("  LinkedIA - Linked Intelligent Analyst".center(70))
    print("  Dove notizie e mercati si incontrano".center(70))
    print("=" * 70 + "\n")

def check_python_version():
    """Verify Python version is compatible"""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("  Attenzione: Python 3.10+ raccomandato")
        return False
    return True

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        print("  File .env non trovato!")
        print("\n   Per configurare l'ambiente:")
        print("   1. Copia .env.example in .env")
        print("   2. Oppure esegui: python setup.py")
        print("\n   Procedere comunque? (s/n): ", end="")
        response = input().strip().lower()
        return response == 's'
    else:
        print("✓ File .env trovato")
        return True

def check_database():
    """Check if database directory exists"""
    db_dir = Path("database")
    if not db_dir.exists():
        print("ℹ  Directory database non trovata - verrà creata automaticamente")
        return True
    else:
        print("✓ Directory database trovata")
        return True

def check_api_keys():
    """Warn about hardcoded API keys"""
    files_with_keys = ["archive_manager.py", "deepseek_manager.py"]
    print("\n  SICUREZZA: Chiavi API rilevate in:")
    for file in files_with_keys:
        if Path(file).exists():
            print(f"   • {file}")
    print("\n   Sistema attivo: DeepSeek AI per analisi pattern")
    print("   Si raccomanda di spostare le chiavi in variabili d'ambiente (.env)")
    return True

def main():
    print_header()
    
    print(" Controlli pre-avvio...\n")
    
    # System checks
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Database Setup", check_database),
        ("API Keys Security", check_api_keys)
    ]
    
    all_passed = True
    for name, check_func in checks:
        try:
            result = check_func()
            all_passed = all_passed and result
        except Exception as e:
            print(f"✗ Errore durante '{name}': {e}")
            all_passed = False
    
    print("\n" + "─" * 70)
    
    if all_passed:
        print("\n✓ Tutti i controlli superati!")
        print("\n Avvio del sistema...\n")
        print("=" * 70 + "\n")
        
        # Import and run main
        try:
            from main import main as run_main
            run_main()
        except KeyboardInterrupt:
            print("\n\n  Esecuzione interrotta dall'utente")
        except Exception as e:
            print(f"\n✗ Errore durante l'esecuzione: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n  Alcuni controlli non sono stati superati")
        print("Vuoi procedere comunque? (s/n): ", end="")
        if input().strip().lower() == 's':
            print("\n Avvio del sistema...\n")
            try:
                from main import main as run_main
                run_main()
            except Exception as e:
                print(f"\n✗ Errore: {e}")
        else:
            print("\nEsecuzione annullata.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nArrivederci! ")
    except Exception as e:
        print(f"\n\n✗ Errore critico: {e}")
        import traceback
        traceback.print_exc()
