import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request
from collections import defaultdict

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v16_3.json"

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

def build_stats_last_7_days():
    stats = defaultdict(lambda: {'for': [], 'against': [], 'forme': ''})
    # On prend les 3 derniers jours pour ne pas exploser le quota
    for i in range(1, 4):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": date}, timeout=15)
            if r.status_code == 200:
                for m in r.json().get('response', []):
                    if m['fixture']['status']['short'] != 'FT': continue
                    h_id = m['teams']['home']['id']
                    a_id = m['teams']['away']['id']
                    h_g = m['goals']['home']
                    a_g = m['goals']['away']
                    if h_g is None or a_g is None: continue
                    
                    # Domicile
                    stats[h_id]['for'].append(h_g)
                    stats[h_id]['against'].append(a_g)
                    if h_g > a_g: stats[h_id]['forme'] += 'W'
                    elif h_g == a_g: stats[h_id]['forme'] += 'D'
                    else: stats[h_id]['forme'] += 'L'
                    
                    # Extérieur
                    stats[a_id]['for'].append(a_g)
                    stats[a_id]['against'].append(h_g)
                    if a_g > h_g: stats[a_id]['forme'] += 'W'
                    elif a_g == h_g: stats[a_id]['forme'] += 'D'
                    else: stats[a_id]['forme'] += 'L'
        except: pass
    return stats

def analyser(stats_dict, fixture):
    league_id = fixture['league']['id']
    if league_id not in LIGUES_TOP_EUROPE: return None
    
    h_id = fixture['teams']['home']['id']
    a_id = fixture['teams']['away']['id']
    h_name = fixture['teams']['home']['name']
    a_name = fixture['teams']['away']['name']

    h = stats_dict.get(h_id, {'for':[1,1,1], 'against':[1,0,1], 'forme':'WDW'})
    a = stats_dict.get(a_id, {'for':[1,1,0], 'against':[1,1,1], 'forme':'LDW'})

    h_avg_for = sum(h['for'][-3:]) / max(1, len(h['for'][-3:]))
    h_avg_against = sum(h['against'][-3:]) / max(1, len(h['against'][-3:]))
    a_avg_for = sum(a['for'][-3:]) / max(1, len(a['for'][-3:]))
    a_avg_against = sum(a['against'][-3:]) / max(1, len(a['against'][-3:]))

    total = h_avg_for + a_avg_for
    
    if total >= 2.5:
        signal = f"✅ Over 1.5 BUTS - Confiance {min(82, int(60+total*8))}%"
    elif total <= 1.5:
        signal = f"⚠️ Under 2.5 - Match fermé - Confiance 70%"
    else:
        signal = f"🔵 Les 2 équipes peuvent marquer - Confiance 68%"

    detail = f"3 derniers réels: {h_name} {h_avg_for:.1f} marqués / {h_avg_against:.1f} encaissés Forme {h['forme'][-3:]}<br>{a_name} {a_avg_for:.1f} / {a_avg_against:.1f} Forme {a['forme'][-3:]}<br>Total moyen réel: {total:.1f} buts"
    return f"{signal}<br><small style='color:#ccc'>{detail}</small>"

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today:
        return cached_data

    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V16.3 - STATS REELS 7 JOURS LAB</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>Basé sur les vrais résultats des 3 derniers jours. Aucun 100% garanti. 18+.</p>"

    if not API_KEY: return html + "<p style='color:red'>API_KEY manquante</p></body></html>"

    try:
        # 1. Stats des 3 derniers jours (3 appels)
        stats_dict = build_stats_last_7_days()
        
        # 2. Matchs du jour (1 appel)
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        data = r.json()
        fixtures = data.get("response", [])
        remaining = r.headers.get('x-ratelimit-requests-remaining','?')
        
        top_matches = [f for f in fixtures if f['league']['id'] in LIGUES_TOP_EUROPE][:3]
        if not top_matches: top_matches = fixtures[:2]

        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | Analyse sur {len(stats_dict)} équipes réelles | Cache 12h</p>"

        for f in top_matches:
            home = f['teams']['home']['name']
            away = f['teams']['away']['name']
            league = f['league']['name']
            time = f['fixture']['date'][11:16]
            html += f"<div style='background:#1a2e1a;border:1px solid #2d5a2d;padding:14px;margin:12px 0;border-radius:12px'>"
            html += f"<b>{home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br><small style='color:#aaa'>{league}</small><br><br>"
            signal = analyser(stats_dict, f)
            html += f"<div style='background:#000;padding:10px;border-radius:8px;line-height:1.5'>{signal}</div></div>"

    except Exception as e:
        html += f"<p style='color:red'>Erreur: {e}</p>"

    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - STATS REELS</a></body></html>"
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
