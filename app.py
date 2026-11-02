import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.getenv("API_KEY", os.getenv("API_FOOT_KEY","")).strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

CACHE_FILE = "/tmp/cache_boss_12h.json"

def get_cache_12h():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                d = json.load(f)
                heure = datetime.fromisoformat(d['heure'])
                if datetime.now() - heure < timedelta(hours=12):
                    return d['data'], d['date']
        except:
            pass
    return None, None

def save_cache_12h(data, date):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'heure': datetime.now().isoformat(), 'data': data, 'date': date}, f)
    except:
        pass

@app.route("/")
def home():
    force = request.args.get("force") == "1"
    today = datetime.utcnow().strftime("%Y-%m-%d")

    cached_data, cached_date = get_cache_12h()
    if not force and cached_data and cached_date == today:
        print(f"✅ CACHE 12h utilisé - 0 appel API")
        return cached_data

    print(f"=== BOSS V15.2 CACHE 12h - Key exists: {bool(API_KEY)} len={len(API_KEY)} ===")
    html = f"<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#111;color:#fff;font-family:sans-serif;padding:10px'>"
    html += f"<h2>⚽ BOSS V15.2 - MATCHS REELS + CACHE 12h</h2>"

    if not API_KEY:
        html += "<p style='color:red'>❌ API_KEY manquante sur Render > Environment</p></body></html>"
        return html

    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        print(f"API Status: {r.status_code} - Remaining: {r.headers.get('x-ratelimit-requests-remaining')}")
        data = r.json()
        print(f"API Response: {data.get('results')} matchs - Errors: {data.get('errors')}")
        
        remaining = r.headers.get('x-ratelimit-requests-remaining', '?')
        html += f"<p style='color:#0f0'>🟢 MATCHS REELS API | Reste: {remaining} | Cache 12h ACTIF | {datetime.utcnow().strftime('%H:%M')} GMT</p>"

        fixtures = data.get("response", [])
        if not fixtures:
            html += f"<p style='border:1px solid orange;padding:10px;color:#ffcc00'>API a répondu 0 match pour {today}. C'est normal si pas de matchs aujourd'hui.</p>"
            html += f"<p style='font-size:10px;color:#888'>Réponse brute: {str(data)[:400]}</p>"
        else:
            for f in fixtures[:20]:
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                league = f['league']['name']
                time = f['fixture']['date'][11:16]
                html += f"<div style='background:#222;padding:10px;margin:8px 0;border-radius:8px'><b>{home} vs {away} - {time}</b><br><small>{league}</small></div>"

    except Exception as e:
        print(f"ERROR: {e}")
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += f"<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:15px;border-radius:8px;text-decoration:none;font-weight:bold'>FORCER ACTU (force=1) - {datetime.utcnow().strftime('%d/%m/%Y')}</a>"
    html += "<p style='color:#666;font-size:11px;margin-top:15px'>Cache 12h fichier: /tmp/cache_boss_12h.json - Tu respectes la règle API-SPORTS</p>"
    html += "</body></html>"
    
    save_cache_12h(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
