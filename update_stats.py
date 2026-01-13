import requests
import json
import sys
import datetime

# --- KONFIGURATION ---
PACKAGE_ID = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"

# Basis-URLs und Server
BASE_URL = "https://fdroid.gitlab.io/metrics"
SERVERS = [
    "http01.fdroid.net",
    "http02.fdroid.net",
    "http03.fdroid.net",
    "originserver.f-droid.org"
]

REPO_PREFIX = "/repo/"
API_PACKAGES_PREFIX = "/api/v1/packages/"

# Rückblick in Wochen (52 = 1 Jahr). 
# Setze das höher (z.B. 150), wenn du die Historie seit Anbeginn der Zeit willst.
LOGS_TO_CHECK = 104 

def format_number(num):
    """
    Gibt die exakte Zahl zurück.
    Beispiel: 1342 -> "1.342" (Deutsche Formatierung)
    """
    # Variante A: Mit Tausender-Punkt (z.B. "1.342")
    return f"{num:,}".replace(",", ".")
    
    # Variante B: Rohdaten ohne alles (z.B. "1342") - falls gewünscht, einkommentieren:
    # return str(num)

def parse_log_file(mirror, filename):
    url = f"{BASE_URL}/{mirror}/{filename}"
    downloads = 0
    api_hits = 0
    versions_found = {}

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return 0, 0, {}
        
        data = r.json()
        paths = data.get("paths", {})

        for path, path_data in paths.items():
            hits = path_data.get("hits", 0) if isinstance(path_data, dict) else path_data
            if hits == 0:
                continue
            
            # APK Downloads prüfen
            if path.startswith(REPO_PREFIX) and path.endswith(".apk"):
                clean_name = path.replace(REPO_PREFIX, "").replace(".apk", "").strip("/")
                if "&" in clean_name:
                    clean_name = clean_name.split("&")[0]
                
                if "_" in clean_name:
                    parts = clean_name.rsplit("_", 1)
                    if len(parts) == 2:
                        pkg_name, version = parts
                        if pkg_name == PACKAGE_ID:
                            downloads += hits
                            versions_found[version] = versions_found.get(version, 0) + hits

            # API Hits prüfen
            elif path == f"{API_PACKAGES_PREFIX}{PACKAGE_ID}":
                api_hits += hits

    except Exception as e:
        print(f"    Fehler in {filename}: {e}")
        return 0, 0, {}

    return downloads, api_hits, versions_found

def main():
    grand_total_downloads = 0
    grand_total_api = 0
    
    print(f"🚀 Starte Analyse für: {PACKAGE_ID}")
    
    for server in SERVERS:
        print(f"\n🌍 Server: {server}")
        try:
            r = requests.get(f"{BASE_URL}/{server}/index.json", timeout=15)
            if r.status_code != 200:
                continue
            
            file_list = r.json()
            file_list.sort()
            
            # Wir nehmen die letzten X Dateien
            recent_files = file_list[-LOGS_TO_CHECK:]
            print(f"   📂 Scanne {len(recent_files)} Logs...")

            server_downloads = 0
            for filename in recent_files:
                if not filename.endswith(".json"): continue
                dl, api, vers = parse_log_file(server, filename)
                
                if dl > 0:
                    server_downloads += dl
                    grand_total_downloads += dl
                    grand_total_api += api

            print(f"   ✅ Zwischensumme {server}: {server_downloads}")

        except Exception as e:
            print(f"   ❌ Fehler bei {server}: {e}")

    print("\n" + "="*40)
    print(f"📦 FINALE SUMME: {grand_total_downloads}")
    print("="*40)

    # JSON schreiben
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(grand_total_downloads),
        "color": "blue" if grand_total_downloads > 0 else "inactive",
        "cacheSeconds": 3600,
        "lastUpdated": now
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)
        
    print(f"💾 {OUTPUT_FILE} gespeichert.")

if __name__ == "__main__":
    main()
