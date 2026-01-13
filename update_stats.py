import requests
import json
import sys
import time

# --- KONFIGURATION ---
PACKAGE_NAME = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"

# Die Basis-URL für die Metriken
BASE_URL = "https://fdroid.gitlab.io/metrics/"

# Die wichtigsten Mirror-Server, die Statistiken liefern.
# http02 und http03 sind die Haupt-Verteiler.
MIRRORS = [
    "http02.fdroid.net",
    "http03.fdroid.net",
    "mirror.f-droid.org" # Manchmal relevant
]

def format_number(num):
    """Formatiert Zahlen (1500 -> 1.5k)"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}k"
    return str(num)

def get_data_from_mirror(mirror):
    """Lädt alle Logs eines Mirrors und summiert die Downloads für das Paket."""
    print(f"\n🔵 Starte Analyse für Mirror: {mirror}")
    
    mirror_index_url = f"{BASE_URL}{mirror}/index.json"
    total_mirror_downloads = 0
    found_any = False
    
    try:
        # 1. Index laden
        r = requests.get(mirror_index_url, timeout=10)
        if r.status_code == 404:
            print(f"   ⚠️ Kein Index gefunden (404).")
            return 0
        r.raise_for_status()
        
        file_list = r.json()
        # Sortieren, damit wir chronologisch vorgehen (optional, aber übersichtlicher)
        file_list.sort()
        
        print(f"   📂 {len(file_list)} Log-Dateien gefunden.")

        # 2. Jede Log-Datei abklappern
        # ACHTUNG: Das können viele Dateien sein. Wir machen das sequenziell.
        for filename in file_list:
            if not filename.endswith(".json"):
                continue

            file_url = f"{BASE_URL}{mirror}/{filename}"
            
            try:
                # Kurzer Sleep, um die Server nicht zu hämmern, falls es viele Requests sind
                # (Bei GitHub Actions meist egal, aber nett sein schadet nicht)
                # time.sleep(0.05) 
                
                log_r = requests.get(file_url, timeout=5)
                if log_r.status_code != 200:
                    continue
                
                data = log_r.json()
                
                # STRUKTUR CHECK:
                # Meistens: { "packages": { "com.olaf.rereminder": 123 } }
                packages = data.get("packages", {})
                
                if PACKAGE_NAME in packages:
                    count = packages[PACKAGE_NAME]
                    # Sicherstellen, dass es eine Zahl ist
                    if isinstance(count, (int, float)):
                        total_mirror_downloads += int(count)
                        found_any = True
                        # Optional: Print für Debugging, wenn man sehen will, wann was passiert
                        # print(f"      + {count} Downloads in {filename}")
                
            except Exception as e:
                # Einzelne Dateifehler ignorieren wir, um den Gesamtprozess nicht zu stoppen
                print(f"   ❌ Fehler bei {filename}: {e}")
                continue

    except Exception as e:
        print(f"   ❌ Fehler beim Mirror {mirror}: {e}")
        return 0

    if found_any:
        print(f"   ✅ Gefunden! Zwischensumme {mirror}: {total_mirror_downloads}")
    else:
        print(f"   ⚪ Keine Daten für {PACKAGE_NAME} auf diesem Mirror.")
        
    return total_mirror_downloads

def main():
    print(f"🔍 Suche nach Statistiken für: {PACKAGE_NAME}")
    
    grand_total = 0
    
    for mirror in MIRRORS:
        grand_total += get_data_from_mirror(mirror)
        
    print(f"\n==========================================")
    print(f"📊 GESAMT DOWNLOADS (alle Mirrors): {grand_total}")
    print(f"==========================================")

    # JSON erstellen
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(grand_total),
        "color": "blue",
        "cacheSeconds": 86400 
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)
    
    print(f"💾 Datei '{OUTPUT_FILE}' wurde gespeichert.")

if __name__ == "__main__":
    main()
