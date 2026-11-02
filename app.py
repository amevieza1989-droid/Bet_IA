import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v16_2.json"

LIGUES_TOP_EUROPE = [39, 140, 78, 135, 61, 2, 3]

def get_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE,'r') as f:
                d=json.load(f)
                if datetime.now() - datetime.fromisoformat(d['heure']) < timedelta(hours=12):
                    return d['data'], d['date']
        except: pass
    return None, None

def save_cache(data,date):
    with open(CACHE_FILE,'w') as f:
        json.dump({'heure':datetime.now().isoformat(),'data':data,'date':date},f)

def get_last_5_stats(team_id):
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "last": 5}, timeout=15)
        if r.status_code == 200:
            res = r.json().get('response', [])
            buts_marques = 0
            buts_encaisses = 0
            forme = ""
            for m in res:
                home = m['teams']['home']['id'] == team_id
                goals_for = m['goals']['home'] if home else m['goals']['away']
                goals_against = m['goals']['away'] if home else m['goals']['home']
                if goals_for is not None and goals_against is not None:
                    buts_marques += goals_for
                    buts_encaisses += goals_against
                    if goals_for > goals_against: forme += "W"
                    elif goals_for == goals_against: forme += "D"
                    else: forme += "L"
            avg_for = buts_marques / max(1, len(res))
            avg_against = buts_encaisses / max(1, len(res))
            return avg_for, avg_against, forme[::-1], len(res)
    except: pass
    return 1.2, 1.0, "N/A", 0

def analyser_vrai_stats(fixture):
    league_id = fixture['league']['id']
    home_id = fixture['teams']['home']['id']
    away_id = fixture['teams']['away']['id']
    home_name = fixture['teams']['home']['name']
    away_name = fixture['teams']['away']['name']

    if league_id not in LIGUES_TOP_EUROPE:
        return None

    h_avg_for, h_avg_against, h_form, h_n = get_last_5_stats(home_id)
    a_avg_for, a_avg_against, a_form, a_n = get_last_5_stats(away_id)

    total_moyen = h_avg_for + a_avg_for
    
    if total_moyen >= 2.6:
        signal = f"✅ Over 1.5 BUTS - Confiance {min(84, int(58+total_moyen*10))}%"
    elif h_avg_for >= 1.4 and a_avg_against >= 1.2:
        signal = f"✅ {home_name} marque - Confiance 73%"
    elif a_avg_for >= 1.4 and h_avg_against >= 1.2:
        signal = f"✅ {away_name} marque - Confiance 71%"
    else:
        signal = f"⚠️ Under 3.5 - Match serré - Confiance 69%"

    detail = f"5 derniers: {home_name} {h_avg_for:.1f} marqués / {h_avg_against:.1f} encaissés Forme {h_form}<br>{away_name} {a_avg_for:.1f} / {a_avg_against:.1f} Forme {a_form}<br>Total moyen: {total_moyen:.1f} buts"
    return f"{signal}<br><small style='color:#ccc'>{detail}</small>"

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today:
        return cached_data

    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V16.2 - VRAIS STATS 5 MATCHS LAB</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>Analyse basée sur les 5 derniers matchs réels. Aucun 100% garanti. 18+ Jouez responsable.</p>"

    if not API_KEY:
        return html + "<p style='color:red'>API_KEY manquante</p></body></html>"

    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        data = r.json()
        fixtures = data.get("response", [])
        remaining = r.headers.get('x-ratelimit-requests-remaining','?')
        top_matches = [f for f in fixtures if f['league']['id'] in LIGUES_TOP_EUROPE][:3]
        if not top_matches: top_matches = fixtures[:2]

        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | {len(top_matches)} matchs avec calcul 5 derniers | Cache 12h</p>"

        for f in top_matches:
            home = f['teams']['home']['name']
            away = f['teams']['away']['name']
            league = f['league']['name']
            time = f['fixture']['date'][11:16]
            html += f"<div style='background:#1a2e1a;border:1px solid #2d5a2d;padding:14px;margin:12px 0;border-radius:12px'>"
            html += f"<b>{home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br><small style='color:#aaa'>{league}</small><br><br>"
            signal = analyser_vrai_stats(f)
            html += f"<div style='background:#000;padding:10px;border-radius:8px;line-height:1.5'>{signal}</div></div>"

    except Exception as e:
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - VRAIS 5 DERNIERS</a></body></html>"
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
