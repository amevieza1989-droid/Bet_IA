import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v27.json"
standings_cache = {}
fixtures_cache = {}

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

def get_standings(league_id):
    if league_id in standings_cache: return standings_cache[league_id]
    season = datetime.utcnow().year
    if datetime.utcnow().month < 7: season -= 1
    result = {}
    for s in [season, season-1, 2024]:
        try:
            r = requests.get(f"{BASE_URL}/standings", headers=HEADERS, params={"league": league_id, "season": s}, timeout=12)
            if r.status_code==200 and r.json().get('response'):
                for group in r.json()['response'][0]['league']['standings']:
                    for t in group:
                        tid = t['team']['id']
                        result[tid] = {
                            'forme': t['form'][-5:] if t['form'] else '?????',
                            'home_for': t['home']['goals']['for']/max(1, t['home']['played']) if t['home']['played'] else 0,
                            'home_against': t['home']['goals']['against']/max(1, t['home']['played']) if t['home']['played'] else 0,
                            'away_for': t['away']['goals']['for']/max(1, t['away']['played']) if t['away']['played'] else 0,
                            'away_against': t['away']['goals']['against']/max(1, t['away']['played']) if t['away']['played'] else 0,
                        }
                break
        except: pass
    standings_cache[league_id] = result
    return result

def get_last_10_reels(team_id):
    if team_id in fixtures_cache: return fixtures_cache[team_id]
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "last": 10, "status": "FT"}, timeout=12)
        if r.status_code==200:
            games = r.json().get('response', [])
            stats = {'total': 0, 'under35': 0, 'over05': 0, 'over15': 0, 'under25': 0, 'goals': [], 'scores': []}
            for g in games:
                hg=g['goals']['home']; ag=g['goals']['away']
                if hg is None or ag is None: continue
                tot=hg+ag
                stats['total']+=1
                stats['goals'].append(tot)
                stats['scores'].append(f"{hg}-{ag}")
                if tot <= 3: stats['under35']+=1
                if tot >= 1: stats['over05']+=1
                if tot >= 2: stats['over15']+=1
                if tot <= 2: stats['under25']+=1
            fixtures_cache[team_id]=stats
            return stats
    except: pass
    return {'total':0,'under35':0,'over05':0,'over15':0,'under25':0,'goals':[],'scores':[]}

def get_h2h(h_id, a_id):
    try:
        r = requests.get(f"{BASE_URL}/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{h_id}-{a_id}", "last": 5}, timeout=10)
        if r.status_code==200:
            games = r.json().get('response', [])
            total=0; cnt=0; scores=[]
            for g in games:
                hg=g['goals']['home']; ag=g['goals']['away']
                if hg is not None and ag is not None:
                    total+=hg+ag; cnt+=1; scores.append(f"{hg}-{ag}")
            if cnt: return total/cnt, " / ".join(scores)
    except: pass
    return None, "Pas de H2H"

def fouille_profonde(fixture):
    league_id = fixture['league']['id']
    h_id = fixture['teams']['home']['id']; a_id = fixture['teams']['away']['id']
    h_name = fixture['teams']['home']['name']; a_name = fixture['teams']['away']['name']
    standings = get_standings(league_id)
    h = standings.get(h_id); a = standings.get(a_id)
    if not h or not a: return None
    h_last = get_last_10_reels(h_id)
    a_last = get_last_10_reels(a_id)
    h2h_avg, h2h_scores = get_h2h(h_id, a_id)
    total_reel = h['home_for'] + a['away_for']
    if h_last['total']>=5 and a_last['total']>=5:
        taux_under35 = (h_last['under35'] + a_last['under35']) / (h_last['total'] + a_last['total']) * 100
        taux_over05 = (h_last['over05'] + a_last['over05']) / (h_last['total'] + a_last['total']) * 100
        taux_over15 = (h_last['over15'] + a_last['over15']) / (h_last['total'] + a_last['total']) * 100
        taux_under25 = (h_last['under25'] + a_last['under25']) / (h_last['total'] + a_last['total']) * 100
    else:
        taux_under35 = taux_over05 = taux_over15 = taux_under25 = 0
    preuves = []
    if h_last['total']: preuves.append(f"{h_name} 10 derniers: {h_last['scores'][:5]}")
    if h2h_avg is not None: preuves.append(f"H2H: {h2h_scores} (moy {h2h_avg:.1f})")
    market=None; conf=0; raison=""
    if taux_under35 >= 80 and total_reel < 2.6:
        market="UNDER 3.5"; conf=84 + min(5, int((taux_under35-80)/3))
        raison=f"En vrai: {taux_under35:.0f}% des 20 derniers matchs sont UNDER 3.5. Il faut 4 buts pour perdre."
    elif taux_over05 >= 90:
        market="OVER 0.5"; conf=83 + min(5, int((taux_over05-90)/2))
        raison=f"En vrai: {taux_over05:.0f}% des 20 derniers matchs ont au moins 1 but. Seul 0-0 fait perdre."
    elif taux_over15 >= 75 and total_reel >= 2.6:
        market="OVER 1.5"; conf=78 + min(5, int((taux_over15-75)/4))
        raison=f"En vrai: {taux_over15:.0f}% des matchs font OVER 1.5. Attaques en feu."
    elif taux_under25 >= 75 and total_reel <= 2.2:
        market="UNDER 2.5"; conf=77 + min(5, int((taux_under25-75)/4))
        raison=f"En vrai: {taux_under25:.0f}% des matchs font UNDER 2.5."
    else: return None
    if conf < 76: return None
    return {'market': market, 'conf': min(89, conf), 'raison': raison, 'preuves': preuves, 'h': h, 'a': a, 'total': total_reel}

def render_ticket(titre, couleur, emoji, matchs, conseil):
    html = f"<div style='background:#111;border:2px solid {couleur};padding:16px;margin:16px 0;border-radius:14px'>"
    html += f"<h3 style='margin:0;color:{couleur}'>{emoji} {titre}</h3><p style='font-size:11px;color:#aaa'>{conseil}</p>"
    for i, (conf, f, res) in enumerate(matchs, 1):
        home = f['teams']['home']['name']; away = f['teams']['away']['name']; league = f['league']['name']; time = f['fixture']['date'][11:16]
        html += f"<div style='background:#000;padding:10px;border-radius:8px;margin:8px 0;line-height:1.5'><b>#{i} {home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br><small style='color:#aaa'>{league}</small><br><b style='color:{couleur}'>🎯 {res['market']} - {conf}%</b><br><small style='color:#ccc'>{res['raison']}</small><br><small style='color:#888'>{' | '.join(res['preuves'][:2])}</small></div>"
    html += "</div>"
    return html

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today: return cached_data
    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V27 FOUILLE REELLE - FIX DATE</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>V27 = V26 + FIX date. Il cherche aujourd'hui, sinon demain. Under/Over seulement. Aucun 100% garanti. 18+.</p>"
    if not API_KEY: return html + "<p style='color:red'>API_KEY manquante</p></body></html>"
    try:
        # FIX DATE: on teste 3 jours, on prend le premier qui a des matchs
        fixtures = []
        date_utilisee = today
        remaining = '?'
        for offset in [0, 1, 2]:
            d = (datetime.utcnow() + timedelta(days=offset)).strftime("%Y-%m-%d")
            r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": d}, timeout=15)
            remaining = r.headers.get('x-ratelimit-requests-remaining','?')
            f_tmp = r.json().get("response", [])
            # On ne garde que les matchs pas encore joués
            f_tmp = [x for x in f_tmp if x['fixture']['status']['short'] in ['NS','TBD']]
            if len(f_tmp) > 0:
                fixtures = f_tmp
                date_utilisee = d
                break
        results = []
        for f in fixtures[:60]:
            res = fouille_profonde(f)
            if res: results.append((res['conf'], f, res))
        results = sorted(results, key=lambda x: x[0], reverse=True)[:10]
        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | Date utilisée: {date_utilisee} | {len(fixtures)} matchs fouillés | {len(results)} SAFE trouvés</p>"
        if len(results) < 3:
            html += f"<div style='background:#2a1a1a;border:1px solid #ff4444;padding:20px;border-radius:12px;text-align:center'><h3>🚫 PAS ASSEZ DE SAFE LE {date_utilisee}</h3><p>Fouille réelle: moins de 3 matchs assez crème. Ne joue pas.</p></div>"
        else:
            html += render_ticket("TICKET SAFE - Les 3 Supers Bons", "#00ff00", "🎯", results[:3], "Les 3 plus crème sur les 10 derniers vrais matchs. Mise normale.")
            if len(results) >= 5:
                html += render_ticket("TICKET FUN - Les 5 Supers Bons", "#ffcc00", "🔥", results[:5], "Petite mise. Les 5 meilleurs.")
            if len(results) > 5:
                html += render_ticket(f"TICKET JACKPOT - Les {len(results)} Bons", "#ff44ff", "💰", results, f"Le gros coup avec les {len(results)} SAFE trouvés. Très petite mise.")
    except Exception as e: html += f"<p style='color:red'>Erreur: {e}</p>"
    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V27 FIX DATE</a></body></html>"
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
