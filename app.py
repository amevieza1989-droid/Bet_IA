import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.getenv("FOOTBALL_DATA_KEY","").strip()
BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": TOKEN}
CACHE_FILE = "/tmp/cache_boss_v34.json"
COMPS = "CL,EL,PL,PD,SA,BL1,FL1,DED,PPL,BSA,CLI,ELC"

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

def get_last_10(team_id):
    try:
        r = requests.get(f"{BASE}/teams/{team_id}/matches", headers=HEADERS, params={"status":"FINISHED","limit":10}, timeout=10)
        if r.status_code != 200: return None
        games = r.json().get('matches',[])
        stats = {'total':0,'under35':0,'over05':0,'over15':0,'scores':[]}
        for g in games:
            s = g.get('score',{}).get('fullTime',{})
            hg=s.get('home'); ag=s.get('away')
            if hg is None or ag is None: continue
            tot=hg+ag; stats['total']+=1; stats['scores'].append(f"{hg}-{ag}")
            if tot<=3: stats['under35']+=1
            if tot>=1: stats['over05']+=1
            if tot>=2: stats['over15']+=1
        return stats
    except: return None

def fouille(match):
    try:
        h_id = match['homeTeam']['id']; a_id = match['awayTeam']['id']
        h_name = match['homeTeam'].get('shortName') or match['homeTeam']['name']
        h_last = get_last_10(h_id); a_last = get_last_10(a_id)
        if not h_last or not a_last: return None
        if h_last['total'] < 4 or a_last['total'] < 4: return None
        tot_n = h_last['total']+a_last['total']
        taux_u35 = (h_last['under35']+a_last['under35'])/tot_n*100
        taux_o05 = (h_last['over05']+a_last['over05'])/tot_n*100
        preuves = [f"{h_name} derniers: {', '.join(h_last['scores'][:5])}"]
        if taux_u35>=70:
            return {'market':"UNDER 3.5",'conf':int(taux_u35),'raison':f"{taux_u35:.0f}% des {tot_n} derniers matchs font 0-3 buts. Il faut 4 buts pour perdre.",'preuves':preuves}
        if taux_o05>=85:
            return {'market':"OVER 0.5",'conf':int(taux_o05),'raison':f"{taux_o05:.0f}% des matchs ont au moins 1 but. Seul 0-0 fait perdre.",'preuves':preuves}
        return None
    except: return None

@app.route("/")
def home():
    force = request.args.get("force")=="1"
    cached = get_cache()
    if not force and cached: return cached
    
    html = "<html><head><meta name='viewport' content='width=device-width'><meta charset='utf-8'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:12px'>"
    html += "<h2>⚽ BOSS V34 - FINAL</h2>"
    
    if not TOKEN:
        return html+"<p style='color:red'>FOOTBALL_DATA_KEY manquante dans Render > Environment</p></body></html>"

    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        date_to = (datetime.utcnow()+timedelta(days=4)).strftime("%Y-%m-%d")
        matches = []
        info = ""
        
        # Essai 1 : avec compétitions
        r = requests.get(f"{BASE}/matches", headers=HEADERS, params={"competitions":COMPS,"dateFrom":today,"dateTo":date_to}, timeout=15)
        if r.status_code == 200:
            matches = r.json().get('matches',[])
            info = f"API OK - {len(matches)} matchs trouvés du {today} au {date_to}"
        elif r.status_code == 403:
            return html+f"<div style='background:#2a1a1a;padding:20px;border-radius:12px;border:1px solid red'><h3>🔴 Token pas encore actif</h3><p>Football-Data dit: 403 Forbidden.<br><br>1. Va dans ta boîte mail<br>2. Clique sur le lien de confirmation de football-data.org<br>3. Attends 5 min<br>4. Reviens cliquer FORCER</p><p style='font-size:10px;color:#888'>{r.text[:300]}</p></div></body></html>"
        else:
            # Essai 2 : sans filtre
            r2 = requests.get(f"{BASE}/matches", headers=HEADERS, params={"dateFrom":today,"dateTo":date_to}, timeout=15)
            if r2.status_code == 200:
                matches = r2.json().get('matches',[])
                info = f"API OK (sans filtre) - {len(matches)} matchs"
            else:
                return html+f"<p style='color:red'>Erreur API {r.status_code}: {r.text[:400]}</p></body></html>"

        # Filtrer que les matchs à venir
        matches = [m for m in matches if m['status'] in ['TIMED','SCHEDULED']]
        total_scan = len(matches)
        
        results = []
        for m in matches[:35]:
            res = fouille(m)
            if res: results.append((res['conf'], m, res))
        
        results = sorted(results, key=lambda x: x[0], reverse=True)[:10]
        
        html+=f"<p style='color:#0f0;background:#111;padding:8px;border-radius:8px'>🟢 {info}<br>📊 {total_scan} à venir scannés | {len(results)} SAFE trouvés</p>"

        if len(results)==0:
            html+=f"<div style='background:#2a1a1a;border:1px solid #ff4444;padding:20px;border-radius:12px;text-align:center'><h3>🚫 PAS DE SAFE AUJOURD'HUI</h3><p>On a scanné {total_scan} matchs, aucun ne respecte 70% UNDER 3.5 ou 85% OVER 0.5.<br><br><b>Conseil BOSS:</b> Ne force pas. Demain c'est Ligue des Champions, il y aura 15 matchs.</p></div>"
        else:
            for idx, (conf,m,res) in enumerate(results[:3],1):
                home=m['homeTeam'].get('shortName') or m['homeTeam']['name']; away=m['awayTeam'].get('shortName') or m['awayTeam']['name']; league=m['competition']['name']; time=m['utcDate'][11:16]
                html+=f"<div style='background:#111;border:2px solid #00ff00;padding:14px;margin:14px 0;border-radius:12px'><b>#{idx} {home} vs {away}</b> <span style='color:#ffcc00'>{time} GMT</span><br><small style='color:#aaa'>{league}</small><br><b style='color:#00ff00'>🎯 {res['market']} - {conf}%</b><br><small style='color:#ccc'>{res['raison']}</small><br><small style='color:#888'>{' | '.join(res['preuves'])}</small></div>"

    except Exception as e:
        html+=f"<p style='color:red'>Erreur technique: {e}</p>"

    html+="<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V34</a>"
    html+="<p style='font-size:10px;color:#666;text-align:center;margin-top:20px'>V34 - Seuils 70% UNDER 3.5 / 85% OVER 0.5 - 18+ Aucun pari n'est sûr à 100%</p></body></html>"
    save_cache(html)
    return html

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
