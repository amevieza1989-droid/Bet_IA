import os, requests
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

CACHE = {"data": None, "date": ""}

@app.route("/")
def home():
    force = request.args.get("force") == "1"
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Cache 6h sauf si force=1
    if not force and CACHE["data"] and CACHE["date"] == today:
        return CACHE["data"]

    print(f"=== BOSS V15.1 START - Key exists: {bool(API_KEY)} len={len(API_KEY)} ===")
    html = f"<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#111;color:#fff;font-family:sans-serif;padding:10px'>"
    html += f"<h2>⚽ BOSS V15.1 - MATCHS REELS</h2>"

    if not API_KEY:
        html += "<p style='color:red'>❌ API_KEY manquante sur Render > Environment</p>"
        return html

    try:
        # Appel API
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        print(f"API Status: {r.status_code} - Remaining: {r.headers.get('x-ratelimit-requests-remaining')}")
        data = r.json()
        print(f"API Response: {data.get('results')} matchs - Errors: {data.get('errors')}")
        
        remaining = r.headers.get('x-ratelimit-requests-remaining', '?')
        used = 100 - int(remaining) if remaining.isdigit() else '?'
        pct = f"{used}%" if isinstance(used,int) else "?"
        
        html += f"<p style='color:#0f0'>🟢 MATCHS REELS API | API: OUI ({pct} Used) | {datetime.utcnow().strftime('%H:%M')} GMT</p>"

        fixtures = data.get("response", [])
        if not fixtures:
            html += f"<p style='border:1px solid red;padding:10px;color:#ff6b6b'>API a répondu 0 match pour {today}. Réponse brute: {str(data)[:500]}</p>"
            html += "<p>Soit il n'y a pas de matchs aujourd'hui, soit ton plan Free est limité. Vérifie sur dashboard.api-football.com</p>"
        else:
            for f in fixtures[:10]:
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                league = f['league']['name']
                time = f['fixture']['date'][11:16]
                html += f"<div style='background:#222;padding:10px;margin:8px 0;border-radius:8px'><b>{home} vs {away} - {time}</b><br><small>{league}</small></div>"

    except Exception as e:
        print(f"ERROR: {e}")
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += f"<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:15px;border-radius:8px;text-decoration:none;font-weight:bold'>ACTUALISER - {datetime.utcnow().strftime('%d/%m/%Y')}</a>"
    html += "</body></html>"
    
    CACHE["data"] = html
    CACHE["date"] = today
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
