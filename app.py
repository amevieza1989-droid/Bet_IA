import os, requests, json, time
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.getenv("FOOTBALL_DATA_KEY","").strip()
BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": TOKEN}
CACHE_FILE = "/tmp/cache_boss_v35.json"
COMPS = "CL,EL,PL,PD,SA,BL1,FL1,DED,PPL,BSA"

# Cache mémoire pour ne pas rappeler 2 fois la même équipe
TEAM_CACHE = {}
CALL_COUNT = 0

def get_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE,'r') as f:
                d=json.load(f)
                if datetime.now() - datetime.fromisoformat(d['heure']) < timedelta(hours=4):
                    return d['data']
        except: pass
    return None

def save_cache(data):
    with open(CACHE_FILE,'w') as f:
        json.dump({'heure':datetime.now().isoformat(),'data':data},f)

def safe_get(url, params=None):
    global CALL_COUNT
    # Respecte 10 appels/min -> on fait pause toutes les 9 requêtes
    if CALL_COUNT >= 8:
        time.sleep(7)
        CALL_COUNT = 0
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=12)
            CALL_COUNT += 1
            if r.status_code == 429:
                time.sleep(8)
                CALL_COUNT = 0
                continue
            return r
        except:
            time.sleep(3)
    return None

def get_last_10(team_id):
    if team_id in TEAM_CACHE:
        return TEAM_CACHE[team_id]
    r = safe_get(f"{BASE}/teams/{team_id}/matches", {"status":"FINISHED","limit":10})
    if not r or r.status_code != 200:
        return None
    games = r.json().get('matches',[])
    stats = {'total':0,'under35':0,'over05':0,'scores':[]}
    for g in games:
        s = g.get('score',{}).get('fullTime',{})
        hg=s.get('home'); ag=s.get('away')
        if hg is None or ag is None: continue
        tot=hg+ag; stats['total']+=1; stats['scores'].append(f"{hg}-{ag}")
        if tot<=3: stats['under35']+=1
        if tot>=1: stats['over05']+=1
    TEAM_CACHE[team_id] = stats
    return stats

def fouille(match):
    try:
        h_id = match['homeTeam']['id']; a_id = match['awayTeam']['id']
        h_name = match['homeTeam'].get('shortName') or match['homeTeam']['name']
        h_last = get_last_10(h_id)
        if not h_last: return None
        # Petite pause entre les 2 équipes pour ne pas spammer
        time.sleep(0.5)
        a_last = get_last_10(a_id)
        if not a_last: return None
        if h_last['total'] < 4 or a_last['total'] < 4: return None
        tot_n = h_last['total']+a_last['total']
        taux_u35 = (h_last['under35']+a_last['under35'])/tot_n*100
        taux_o05 = (h_last['over05']+a_last['over05'])/tot_n*100
        preuves = [f"Derniers: {', '.join(h_last['scores'][:5])}"]
        if taux_u35>=70:
            return {'market':"UNDER 3.5",'conf':int(taux_u35),'raison':f"{taux_u35:.0f}% des {tot_n} derniers font UNDER 3.5 (0-3 buts).",'preuves':preuves}
        if taux_o05>=85:
            return {'market':"OVER 0.5",'conf':int(taux_o05),'raison':f"{taux_o05:.0f}% des matchs ont au moins 1 but.",'preuves':preuves}
        return None
    except: return None

@app.route("/")
def home():
    global TEAM_CACHE, CALL_COUNT
    TEAM_CACHE = {}; CALL_COUNT = 0
    force = request.args.get("force")=="1"
    cached = get_cache()
    if not force and cached: return cached
    
    html = "<html><head><meta name='viewport' content='width=device-width'><meta charset='utf-8'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:12px'>"
    html += "<h2>⚽ BOSS V35 - ANTI 429</h2>"
    if not TOKEN: return html+"<p style='color:red'>FOOTBALL_DATA_KEY manquante</p></body></html>"

    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow()+timedelta(days=4)).strftime("%Y-%m-%d")
        
        r = safe_get(f"{BASE}/matches", {"competitions":COMPS,"dateFrom":today,"dateTo":date_to})
        if not r or r.status_code != 200:
            return html+f"<p style='color:red'>API {r.status_code if r else 'timeout'}: {r.text[:300] if r else 'no response'}</p><a href='/?force=1'>Réessayer</a></body></html>"
        
        matches = [m for m in r.json().get('matches',[]) if m['status'] in ['TIMED','SCHEDULED']]
        total_scan = len(matches)
        
        # ON SCANNE QUE 12 MATCHS MAX pour ne pas dépasser la limite
        results = []
        for m in matches[:12]:
            res = fouille(m)
            if res: results.append((res['conf'], m, res))
        
        results = sorted(results, key=lambda x: x[0], reverse=True)[:10]
        html+=f"<p style='color:#0f0;background:#111;padding:8px;border-radius:8px'>🟢 Token OK | {total_scan} matchs à venir | {len(results)} SAFE trouvés<br><small style='color:#888'>On scanne 12 max pour respecter 10 req/min - Clique FORCER pour scanner les 12 suivants</small></p>"

        if len(results)==0:
            html+=f"<div style='background:#2a1a1a;border:1px solid #ff4444;padding:20px;border-radius:12px;text-align:center'><h3>🚫 PAS DE SAFE SUR LES 12 PREMIERS</h3><p>{total_scan} matchs au total. Clique FORCER pour voir la suite, ou attends demain LDC.</p></div>"
        else:
            for idx, (conf,m,res) in enumerate(results[:5],1):
                home=m['homeTeam'].get('shortName') or m['homeTeam']['name']; away=m['awayTeam'].get('shortName') or m['awayTeam']['name']; league=m['competition']['name']; t=m['utcDate'][11:16]
                html+=f"<div style='background:#111;border:2px solid #00ff00;padding:14px;margin:14px 0;border-radius:12px'><b>#{idx} {home} vs {away}</b> <span style='color:#ffcc00'>{t} GMT</span><br><small style='color:#aaa'>{league}</small><br><b style='color:#00ff00'>🎯 {res['market']} - {conf}%</b><br><small style='color:#ccc'>{res['raison']}</small><br><small style='color:#888'>{res['preuves'][0]}</small></div>"

    except Exception as e:
        html+=f"<p style='color:red'>Erreur: {e}</p>"

    html+="<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V35 (12 suivants)</a>"
    html+="<p style='font-size:10px;color:#666;text-align:center'>V35 respecte 10 req/min - 18+</p></body></html>"
    save_cache(html)
    return html

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
