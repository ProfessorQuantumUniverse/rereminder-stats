import requests
import json
import sys

# Konfiguration
# Wir prüfen die Haupt-Mirrors für Downloads
MIRRORS = [
    "http02.fdroid.net",
    "http03.fdroid.net",
    "originserver.f-droid.org"
]
BASE_URL = "https://fdroid.gitlab.io/metrics/"
PACKAGE_NAME = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"
# Anzahl der letzten Log-Dateien, die pro Mirror geprüft werden (1 Log = 1 Woche)
# 12 Wochen = ca. 3 Monate Rückblick
LOGS_TO_CHECK = 12 

def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}k"
    return str(num)

def get_downloads_for_mirror(mirror):
    print(f"--- Prüfe Mirror: {mirror} ---")
    index_url = f"{BASE_URL}{mirror}/index.json"
    total_mirror_downloads = 0
    
    try:
        # 1. Index laden (Liste der verfügbaren Datum-Logfiles)
        r = requests.get(index_url)
        if r.status_code == 404:
            print(f"Kein Index gefunden für {mirror} (überspringe)")
            return 0
        r.raise_for_status()
        
        files = r.json()
        if not files:
            return 0
            
        # Sortieren und die neuesten X Dateien nehmen
        files.sort()
        recent_files = files[-LOGS_TO_CHECK:]
        print(f"Analysiere {len(recent_files)} Logs von {recent_files[0]} bis {recent_files[-1]}")

        # 2. Jedes Logfile laden und parsen
        for filename in recent_files:
            if not filename.endswith(".json"):
                filename += ".json"
            
            file_url = f"{BASE_URL}{mirror}/{filename}"
            try:
                # Timeout wichtig, damit es nicht ewig hängt
                log_r = requests.get(file_url, timeout=10)
                if log_r.status_code != 200:
                    continue
                    
                data = log_r.json()
                
                # F-Droid Metriken haben die Pfade oft unter 'paths'
                # Format: { "paths": { "/repo/com.olaf.rereminder_10.apk": 123, ... } }
                paths = data.get("paths", {})
                
                for path, count in paths.items():
                    # Wir suchen nach Pfaden, die den Paketnamen und .apk enthalten
                    # Pfade sehen oft so aus: /repo/com.beispiel.app_102.apk
                    if PACKAGE_NAME in path and path.endswith(".apk"):
                        total_mirror_downloads += int(count)
                        
            except Exception as e:
                print(f"Fehler bei Datei {filename}: {e}")
                continue

    except Exception as e:
        print(f"Fehler beim Spiegel {mirror}: {e}")
        return 0
    
    print(f"Downloads auf {mirror}: {total_mirror_downloads}")
    return total_mirror_downloads

def main():
    total_downloads = 0
    
    # Alle Mirrors abklappern
    for mirror in MIRRORS:
        total_downloads += get_downloads_for_mirror(mirror)
    
    print(f"\nGESAMT DOWNLOADS (letzte {LOGS_TO_CHECK} Wochen): {total_downloads}")

    # JSON für Shields.io erstellen
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(total_downloads),
        "color": "blue",
        "cacheSeconds": 86400 # Cache für 24h
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)
    
    print(f"Datei '{OUTPUT_FILE}' erfolgreich erstellt.")

if __name__ == "__main__":
    main()
