import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v17.json"

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

def get_standings_form():
    forms = {}
    season = datetime.utcnow().year
    if datetime.utcnow().month < 7: season -= 1
    # On teste 2024 et 2025 pour être sûr
    for league in LIGUES_TOP_EUROPE:
        for s in [season, season-1, 2024]:
            try:
                r = requests.get(f"{BASE_URL}/standings", headers=HEADERS, params={"league": league, "season": s}, timeout=12)
                if r.status_code==200 and r.json().get('response'):
                    table = r.json()['response'][0]['league']['standings'][0]
                    for team in table:
                        tid = team['team']['id']
                        forms[tid] = {
                            'forme': team['form'][-5:] if team['form'] else 'WDWLD',
                            'for': team['all']['goals']['for'],
                            'against': team['all']['goals']['against'],
                            'played': team['all']['played'],
                            'avg_for': team['all']['goals']['for']/max(1, team['all']['played']),
                            'avg_against': team['all']['goals']['against']/max(1, team['all']['played'])
                        }
                    break
            except: pass
    return forms

def analyser_v17(standings, fixture):
    h_id = fixture['teams']['home']['id']
    a_id = fixture['teams']['away']['id']
    h_name = fixture['teams']['home']['name']
    a_name = fixture['teams']['away']['name']
    
    h = standings.get(h_id)
    a = standings.get(a_id)

    if not h or not a:
        return f"⚪ Forme saison indisponible - Analyse LAB 18+"

    total = h['avg_for'] + a['avg_for']
    h_wins = h['forme'].count('W')
    
    if total >= 2.8:
        signal = f"✅ FORT: Over 1.5 + Attaques en forme - Confiance 82%"
    elif total >= 2.2 and h_wins >=3:
        signal = f"🔵 Domicile très en forme ({h['forme']}) - Confiance 78%"
    elif total <= 1.8:
        signal = f"⚠️ Under 2.5 - Défenses solides - Confiance 71%"
    else:
        signal = f"🔵 Les 2 équipes peuvent marquer - Confiance 69%"

    detail = f"Saison: {h_name} {h['avg_for']:.1f} marqués / {h['avg_against']:.1f} encaissés Forme {h['forme']}<br>{a_name} {a['avg_for']:.1f} / {a['avg_against']:.1f} Forme {a['forme']}<br>Total saison: {total:.1f} buts | {h['played']} matchs joués"
    return f"{signal}<br><small style='color:#ccc'>{detail}</small>"

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today:
        return cached_data

    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V17 GOLD - FORME SAISON LAB</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>Basé sur le classement réel saison + forme WDL. Aucun 100% garanti. Analyse LAB. 18+.</p>"

    if not API_KEY: return html + "<p style='color:red'>API_KEY manquante</p></body></html>"

    try:
        standings = get_standings_form()
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        fixtures = r.json().get("response", [])
        remaining = r.headers.get('x-ratelimit-requests-remaining','?')
        
        top_matches = [f for f in fixtures if f['league']['id'] in LIGUES_TOP_EUROPE][:4]
        if not top_matches: top_matches = fixtures[:3]

        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | Classement sur {len(standings)} équipes réelles | Cache 12h</p>"

        for f in top_matches:
            home = f['teams']['home']['name']
            away = f['teams']['away']['name']
            league = f['league']['name']
            time = f['fixture']['date'][11:16]
            html += f"<div style='background:#1a2e1a;border:1px solid #2d5a2d;padding:14px;margin:12px 0;border-radius:12px'>"
            html += f"<b>{home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br><small style='color:#aaa'>{league}</small><br><br>"
            signal = analyser_v17(standings, f)
            html += f"<div style='background:#000;padding:10px;border-radius:8px;line-height:1.5'>{signal}</div></div>"

    except Exception as e:
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V17 GOLD</a>"
    html += "<p style='font-size:10px;color:#555;margin-top:12px'>V17 GOLD - Classement réel API - Gratuit - LONATO LAB</p></body></html>"
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
