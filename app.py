import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
API_KEY = os.getenv("API_KEY","").strip()
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
CACHE_FILE = "/tmp/cache_boss_v24.json"
standings_cache = {}

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
                            'played': max(1, t['all']['played']),
                            'home_for': t['home']['goals']['for']/max(1, t['home']['played']) if t['home']['played'] else 0,
                            'home_against': t['home']['goals']['against']/max(1, t['home']['played']) if t['home']['played'] else 0,
                            'away_for': t['away']['goals']['for']/max(1, t['away']['played']) if t['away']['played'] else 0,
                            'away_against': t['away']['goals']['against']/max(1, t['away']['played']) if t['away']['played'] else 0,
                        }
                break
        except: pass
    standings_cache[league_id] = result
    return result

def get_h2h(h_id, a_id):
    try:
        r = requests.get(f"{BASE_URL}/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{h_id}-{a_id}", "last": 5}, timeout=10)
        if r.status_code==200:
            games = r.json().get('response', [])
            total=0; cnt=0
            for g in games:
                hg=g['goals']['home']; ag=g['goals']['away']
                if hg is not None and ag is not None:
                    total+=hg+ag; cnt+=1
            if cnt: return total/cnt
    except: pass
    return None

def fouille_profonde(fixture):
    league_id = fixture['league']['id']
    h_id = fixture['teams']['home']['id']; a_id = fixture['teams']['away']['id']
    h_name = fixture['teams']['home']['name']; a_name = fixture['teams']['away']['name']
    standings = get_standings(league_id)
    h = standings.get(h_id); a = standings.get(a_id)
    if not h or not a: return None

    h2h_avg = get_h2h(h_id, a_id)
    total_reel = h['home_for'] + a['away_for']

    score = 0; preuves = []
    if a['away_for'] < 1.0: score+=2; preuves.append(f"{a_name} {a['away_for']:.1f} à l'ext")
    if h['home_against'] < 0.9: score+=1; preuves.append(f"{h_name} {h['home_against']:.1f} encaissé dom")
    if h['home_for'] >= 1.8: score+=1; preuves.append(f"{h_name} {h['home_for']:.1f} marqué dom")
    if h['forme'].count('W')>=3: score+=1
    if a['forme'].count('L')>=2: score+=1; preuves.append(f"{a_name} crise {a['forme']}")
    if h2h_avg is not None:
        if h2h_avg < 2.0: score+=2; preuves.append(f"H2H {h2h_avg:.1f} buts")
        elif h2h_avg >= 3.0: score+=2; preuves.append(f"H2H {h2h_avg:.1f} buts")

    # LE BOT CHOISIT LE MARCHE LE PLUS CREME POUR CE MATCH
    market=None; conf=0
    if total_reel < 2.4 and a['away_for'] < 1.1:
        market="UNDER 3.5"; conf=84+min(6,score); raison=f"Total {total_reel:.1f}. Il faut 4 buts pour perdre."
    elif total_reel >= 1.6 and total_reel < 2.6 and h['home_for']>=1.0 and a['away_for']>=0.8:
        market="OVER 0.5"; conf=83+min(5,score); raison="Les 2 marquent. Il faut juste 1 but."
    elif total_reel >= 2.8:
        market="OVER 1.5"; conf=78+min(5,score); raison=f"Total {total_reel:.1f}. Attaques en feu."
    elif total_reel <= 2.0:
        market="UNDER 2.5"; conf=76+min(5,score); raison=f"Total {total_reel:.1f}. Défenses solides."
    else: return None
    if conf < 76: return None
    return {'market': market, 'conf': min(89, conf), 'raison': raison, 'preuves': preuves, 'h': h, 'a': a, 'total': total_reel}

def render_ticket(titre, couleur, emoji, matchs, conseil):
    html = f"<div style='background:#111;border:2px solid {couleur};padding:16px;margin:16px 0;border-radius:14px'>"
    html += f"<h3 style='margin:0;color:{couleur}'>{emoji} {titre}</h3><p style='font-size:11px;color:#aaa'>{conseil}</p>"
    for i, (conf, f, res) in enumerate(matchs, 1):
        home = f['teams']['home']['name']; away = f['teams']['away']['name']; league = f['league']['name']; time = f['fixture']['date'][11:16]
        html += f"<div style='background:#000;padding:10px;border-radius:8px;margin:8px 0;line-height:1.5'><b>#{i} {home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT</span><br><small style='color:#aaa'>{league}</small><br><b style='color:{couleur}'>🎯 {res['market']} - {conf}%</b><br><small style='color:#ccc'>{res['raison']} | {res['h']['forme']} vs {res['a']['forme']}</small></div>"
    html += "</div>"
    return html

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cached_data, cached_date = get_cache()
    if not force and cached_data and cached_date == today: return cached_data
    html = "<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html += "<h2>⚽ BOSS V24 - 3 TICKETS LAB</h2>"
    html += "<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>V24 fouille profond, trie les 10 meilleurs, et te fait 3 tickets. Aucun 100% garanti. 18+. Joue responsable.</p>"
    if not API_KEY: return html + "<p style='color:red'>API_KEY manquante</p></body></html>"
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": today}, timeout=15)
        fixtures = r.json().get("response", [])
        remaining = r.headers.get('x-ratelimit-requests-remaining','?')
        results = []
        for f in fixtures[:40]:
            res = fouille_profonde(f)
            if res: results.append((res['conf'], f, res))
        results = sorted(results, key=lambda x: x[0], reverse=True)[:10]
        html += f"<p style='color:#0f0'>🟢 API Reste: {remaining} | {len(fixtures)} matchs fouillés | {len(results)} SAFE trouvés</p>"
        if len(results) < 3:
            html += "<div style='background:#2a1a1a;border:1px solid #ff4444;padding:20px;border-radius:12px;text-align:center'><h3>🚫 PAS ASSEZ DE SAFE AUJOURD'HUI</h3><p>Le bot a fouillé, moins de 3 matchs assez crème. Ne joue pas aujourd'hui.</p></div>"
        else:
            # === LES 3 TICKETS ===
            ticket_safe = results[:3]
            ticket_fun = results[:5]
            ticket_jackpot = results[:10]
            html += render_ticket("TICKET SAFE - Les 3 Supers Bons", "#00ff00", "🎯", ticket_safe, "Ton ticket de tous les jours. Les 3 plus crème. Mise normale. Si tu ne joues qu'un seul ticket, c'est celui-là.")
            if len(results) >= 5:
                html += render_ticket("TICKET FUN - Les 5 Supers Bons", "#ffcc00", "🔥", ticket_fun, "Pour le fun, un peu plus de cote. Petite mise. Les 5 meilleurs.")
            if len(results) >= 8:
                html += render_ticket("TICKET JACKPOT - Les 10 Bons", "#ff44ff", "💰", ticket_jackpot, "Le gros coup. Petite mise seulement. 10 matchs, c'est pour tenter le jackpot, pas pour sécuriser.")
            html += "<div style='background:#222;padding:12px;border-radius:8px;font-size:12px'><b>💡 REGLE BOSS:</b><br>SAFE = mise normale (ex: 500 XOF)<br>FUN = petite mise (ex: 200 XOF)<br>JACKPOT = très petite mise (ex: 100 XOF)<br>Jamais tout sur JACKPOT.</div>"
    except Exception as e: html += f"<p style='color:red'>Erreur: {e}</p>"
    html += "<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V24 3 TICKETS</a></body></html>"
    save_cache(html, today)
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
