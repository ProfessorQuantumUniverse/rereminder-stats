import requests
import json
import sys
import datetime

# --- KONFIGURATION ---
PACKAGE_NAME = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"
BASE_URL = "https://fdroid.gitlab.io/metrics/"

# http02 und http03 sind die Hauptquellen
MIRRORS = [
    "http02.fdroid.net",
    "http03.fdroid.net"
]

def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}k"
    return str(num)

def get_data_from_mirror(mirror):
    print(f"\n🔵 --- Mirror: {mirror} ---")
    index_url = f"{BASE_URL}{mirror}/index.json"
    total_mirror = 0
    
    try:
        r = requests.get(index_url, timeout=15)
        if r.status_code != 200:
            print(f"   ⚠️ Index nicht erreichbar ({r.status_code})")
            return 0
        
        file_list = r.json()
        if not file_list: return 0
        
        # Wir nehmen ALLES was da ist. 
        # Falls das Script zu lange läuft (Timeout), reduziere dies auf z.B. file_list[-50:]
        file_list.sort()
        # Wir nehmen die letzten 50 Logs (ca. 1 Jahr), um sicherzugehen
        recent_files = file_list[-50:] 
        
        print(f"   📂 Scanne {len(recent_files)} Logs (von {len(file_list)} verfügbaren)...")

        for filename in recent_files:
            if not filename.endswith(".json"): continue
            
            try:
                log_r = requests.get(f"{BASE_URL}{mirror}/{filename}", timeout=5)
                if log_r.status_code != 200: continue
                
                data = log_r.json()
                file_hits = 0

                # STRATEGIE 1: Suche in 'paths' (häufigste Form bei Raw Logs)
                # Schlüssel sind z.B. "/repo/com.olaf.rereminder_102.apk"
                paths = data.get("paths", {})
                for path, count in paths.items():
                    if PACKAGE_NAME in path and str(path).endswith(".apk"):
                        file_hits += int(count)

                # STRATEGIE 2: Suche in 'packages' (falls aggregiert)
                packages = data.get("packages", {})
                if PACKAGE_NAME in packages:
                    file_hits += int(packages[PACKAGE_NAME])

                # STRATEGIE 3: Root Level (selten, aber möglich)
                if PACKAGE_NAME in data and isinstance(data[PACKAGE_NAME], (int, float)):
                     file_hits += int(data[PACKAGE_NAME])

                if file_hits > 0:
                    # print(f"      + {file_hits} in {filename}") # Auskommentieren für weniger Spam
                    total_mirror += file_hits

            except Exception:
                pass 
                
    except Exception as e:
        print(f"   ❌ Fehler: {e}")
        return 0
    
    print(f"   ✅ Zwischensumme {mirror}: {total_mirror}")
    return total_mirror

def main():
    grand_total = 0
    
    # 1. Daten sammeln
    for mirror in MIRRORS:
        grand_total += get_data_from_mirror(mirror)
    
    print(f"\n==========================================")
    print(f"📊 FINALE SUMME: {grand_total}")
    print(f"==========================================")

    # 2. JSON schreiben (mit Timestamp für erzwungenen Commit)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(grand_total),
        "color": "blue" if grand_total > 0 else "inactive",
        "cacheSeconds": 3600,
        "lastUpdated": now
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)

if __name__ == "__main__":
    main()
