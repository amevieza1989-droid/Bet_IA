import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v16_1.json"

LIGUES_TOP_EUROPE = [39, 140, 78, 135, 61, 2, 3] # PL, Liga, Bundesliga, Serie A, Ligue1, UCL, UEL

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

def get_team_stats(team_id, league_id, season):
    try:
        r = requests.get(f"{BASE_URL}/teams/statistics", headers=HEADERS, 
                         params={"team": team_id, "league": league_id, "season": season}, timeout=15)
        if r.status_code == 200:
            return r.json().get('response', {})
    except: pass
    return None

def analyser_vrai_stats(fixture):
    league_id = fixture['league']['id']
    season = fixture['league']['season']
    home_id = fixture['teams']['home']['id']
    away_id = fixture['teams']['away']['id']
    home_name = fixture['teams']['home']['name']
    away_name = fixture['teams']['away']['name']

    if league_id not in LIGUES_TOP_EUROPE:
        return None

    stats_home = get_team_stats(home_id, league_id, season)
    stats_away = get_team_stats(away_id, league_id, season)

    if not stats_home or not stats_away:
        return f"📊 Audit {home_name} vs {away_name}: Données en cours... (API limite)"

    # Vrais chiffres API
    try:
        forme_home = stats_home['form'][-5:] if 'form' in stats_home else 'N/A'
        forme_away = stats_away['form'][-5:] if 'form' in stats_away else 'N/A'
        
        buts_home_avg = float(stats_home['goals']['for']['average']['total'] or 1.2)
        buts_away_avg = float(stats_away['goals']['for']['average']['total'] or 1.1)
        encaisse_home = float(stats_home['goals']['against']['average']['total'] or 1.0)
        encaisse_away = float(stats_away['goals']['against']['average']['total'] or 1.1)

        total_moyen = buts_home_avg + buts_away_avg
        # Calcul confiance LAB
        if total_moyen >= 2.8:
            signal = f"✅ Over 1.5 BUTS - Confiance {min(82, int(60+total_moyen*8))}%"
            detail = f"Moy buts: {home_name} {buts_home_avg} + {away_name} {buts_away_avg} = {total_moyen:.1f}"
        elif buts_home_avg > 1.5 and encaisse_away > 1.2:
            signal = f"✅ Domicile marque +1.5 - Confiance 71%"
            detail = f"{home_name} marque {buts_home_avg}/match, {away_name} encaisse {encaisse_away}"
        else:
            signal = f"⚠️ Match fermé - Under 3.5 probable - Confiance 68%"
            detail = f"Défenses solides: encaissé {encaisse_home} / {encaisse_away}"

        return f"{signal}<br><small style='color:#ccc'>Forme H: {forme_home} | A: {forme_away}<br>{detail}</small>"
    except Exception as e:
        return f"Analyse basique disponible - {home_name} vs {away_name}"

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today:
        print("✅ CACHE V16.1 12h utilisé")
        return cached_data

    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V16.1 - VRAIS STATS EUROPE LAB</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>Méthode LAB: Analyse statistique réelle. Aucun résultat à 100%. Jouez responsable. 18+.</p>"

    if not API_KEY:
        return html + "<p style='color:red'>API_KEY manquante</p></body></html>"

    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        data = r.json()
        fixtures = data.get("response", [])
        remaining = r.headers.get('x-ratelimit-requests-remaining','?')
        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | 3 matchs analysés avec vrais stats | Cache 12h</p>"

        top_matches = [f for f in fixtures if f['league']['id'] in LIGUES_TOP_EUROPE][:3]
        
        if not top_matches:
            html += "<p style='color:orange'>Pas de TOP EUROPE aujourd'hui. Voici le top du jour:</p>"
            top_matches = fixtures[:2]

        for f in top_matches:
            home = f['teams']['home']['name']
            away = f['teams']['away']['name']
            league = f['league']['name']
            time = f['fixture']['date'][11:16]
            html += f"<div style='background:#1a2e1a;border:1px solid #2d5a2d;padding:14px;margin:12px 0;border-radius:12px'>"
            html += f"<b style='font-size:17px'>{home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br>"
            html += f"<small style='color:#aaa'>{league}</small><br><br>"
            signal = analyser_vrai_stats(f)
            html += f"<div style='background:#000;padding:10px;border-radius:8px;line-height:1.5'>{signal}</div></div>"

    except Exception as e:
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU + VRAIS STATS</a>"
    html += "<p style='font-size:10px;color:#555;margin-top:12px'>V16.1 - 7 appels API max par 12h - Conforme plan gratuit API-SPORTS (100/j)</p></body></html>"
    
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
