import requests
import json
import sys
import datetime
import random

# --- KONFIGURATION ---
PACKAGE_NAME = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"
BASE_URL = "https://fdroid.gitlab.io/metrics/"

# Die Mirror-Server
MIRRORS = [
    "http02.fdroid.net",
    "http03.fdroid.net"
]

def format_number(num):
    if num >= 1_000_000: return f"{num/1000000:.1f}M"
    if num >= 1_000: return f"{num/1000:.1f}k"
    return str(num)

def get_data_from_mirror(mirror):
    print(f"\n🔵 --- Mirror: {mirror} ---")
    try:
        # 1. Index laden
        r = requests.get(f"{BASE_URL}{mirror}/index.json", timeout=15)
        if r.status_code != 200:
            print(f"   ⚠️ Index nicht erreichbar ({r.status_code})")
            return 0
        
        file_list = r.json()
        if not file_list: return 0
        
        # Wir nehmen nur die allerneueste Datei zum Testen der Verbindung
        # Später im Echteinsatz: file_list[-50:]
        file_list.sort()
        latest_files = file_list[-5:] 
        
        print(f"   📂 Scanne die letzten {len(latest_files)} Logs...")

        total_mirror = 0
        debug_samples = []

        for filename in latest_files:
            if not filename.endswith(".json"): continue
            
            try:
                log_r = requests.get(f"{BASE_URL}{mirror}/{filename}", timeout=10)
                if log_r.status_code != 200: continue
                
                data = log_r.json()
                
                # Prüfen auf 'paths' (Raw Logs)
                paths = data.get("paths", {})
                
                # --- DEBUG: Zeige mir irgendwelche Apps, um zu beweisen, dass Daten da sind ---
                if not debug_samples and paths:
                    # Nimm 3 zufällige Einträge aus diesem Log
                    keys = list(paths.keys())
                    sample = random.sample(keys, min(3, len(keys)))
                    debug_samples.extend(sample)

                # --- ECHTE SUCHE ---
                for path, count in paths.items():
                    # Suche nach deinem Paketnamen im Pfad
                    if PACKAGE_NAME in path:
                        print(f"      ✅ TREFFER! {path}: {count} Downloads")
                        total_mirror += int(count)

            except Exception:
                pass 
        
        # Zeige dem User, was wir gefunden haben (fremde Apps)
        if debug_samples:
            print(f"   ℹ️ Beweis, dass Logs gelesen werden (zufällige Funde):")
            for sample in debug_samples:
                print(f"      - {sample}")
        else:
            print("   ⚠️ Warnung: Log-Datei war leer oder hatte keine 'paths' Struktur.")

    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return 0
    
    return total_mirror

def main():
    grand_total = 0
    for mirror in MIRRORS:
        grand_total += get_data_from_mirror(mirror)
    
    print(f"\n==========================================")
    print(f"📊 DEINE APP ({PACKAGE_NAME}): {grand_total}")
    print(f"==========================================")

    # JSON schreiben
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(grand_total),
        "color": "blue" if grand_total > 0 else "inactive",
        "lastUpdated": now
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)

if __name__ == "__main__":
    main()
