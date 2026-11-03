import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.getenv("FOOTBALL_DATA_KEY","").strip()
BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": TOKEN}
CACHE_FILE = "/tmp/cache_boss_v32.json"

# Codes Football-Data gratuits
COMPS = "CL,EL,PL,SA,PD,BL1,FL1,DED,PPL,BSA,CLI"

def get_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE,'r') as f:
                d=json.load(f)
                if datetime.now() - datetime.fromisoformat(d['heure']) < timedelta(hours=6):
                    return d['data'], d['date']
        except: pass
    return None, None

def save_cache(data,date):
    with open(CACHE_FILE,'w') as f:
        json.dump({'heure':datetime.now().isoformat(),'data':data,'date':date},f)

def get_last_10(team_id):
    try:
        r = requests.get(f"{BASE}/teams/{team_id}/matches", headers=HEADERS, params={"status":"FINISHED","limit":10}, timeout=12)
        if r.status_code==200:
            games = r.json().get('matches',[])
            stats = {'total':0,'under35':0,'over05':0,'over15':0,'under25':0,'scores':[]}
            for g in games:
                s = g.get('score',{}).get('fullTime',{})
                hg=s.get('home'); ag=s.get('away')
                if hg is None or ag is None: continue
                tot=hg+ag; stats['total']+=1; stats['scores'].append(f"{hg}-{ag}")
                if tot<=3: stats['under35']+=1
                if tot>=1: stats['over05']+=1
                if tot>=2: stats['over15']+=1
                if tot<=2: stats['under25']+=1
            return stats
    except: pass
    return {'total':0,'under35':0,'over05':0,'over15':0,'under25':0,'scores':[]}

def fouille(match):
    h_id = match['homeTeam']['id']; a_id = match['awayTeam']['id']
    h_name = match['homeTeam'].get('shortName') or match['homeTeam']['name']
    h_last = get_last_10(h_id); a_last = get_last_10(a_id)
    if h_last['total'] < 3 or a_last['total'] < 3: return None
    tot_n = h_last['total']+a_last['total']
    taux_u35 = (h_last['under35']+a_last['under35'])/tot_n*100
    taux_o05 = (h_last['over05']+a_last['over05'])/tot_n*100
    taux_o15 = (h_last['over15']+a_last['over15'])/tot_n*100
    taux_u25 = (h_last['under25']+a_last['under25'])/tot_n*100
    preuves = [f"{h_name} derniers: {h_last['scores'][:5]}"]
    if taux_u35>=70:
        return {'market':"UNDER 3.5",'conf':min(88,72+int((taux_u35-70)/2)),'raison':f"En vrai: {taux_u35:.0f}% des {tot_n} derniers matchs sont UNDER 3.5. Il faut 4 buts pour perdre.",'preuves':preuves}
    if taux_o05>=85:
        return {'market':"OVER 0.5",'conf':min(88,72+int((taux_o05-85)/2)),'raison':f"En vrai: {taux_o05:.0f}% des matchs ont au moins 1 but. Seul 0-0 fait perdre.",'preuves':preuves}
    if taux_o15>=65:
        return {'market':"OVER 1.5",'conf':min(88,70+int((taux_o15-65)/3)),'raison':f"En vrai: {taux_o15:.0f}% des matchs font OVER 1.5.",'preuves':preuves}
    if taux_u25>=65:
        return {'market':"UNDER 2.5",'conf':min(88,70+int((taux_u25-65)/3)),'raison':f"En vrai: {taux_u25:.0f}% des matchs font UNDER 2.5.",'preuves':preuves}
    return None

def render_ticket(titre,couleur,emoji,matchs,conseil):
    html=f"<div style='background:#111;border:2px solid {couleur};padding:16px;margin:16px 0;border-radius:14px'><h3 style='margin:0;color:{couleur}'>{emoji} {titre}</h3><p style='font-size:11px;color:#aaa'>{conseil}</p>"
    for i,(conf,m,res) in enumerate(matchs,1):
        home=m['homeTeam'].get('shortName') or m['homeTeam']['name']; away=m['awayTeam'].get('shortName') or m['awayTeam']['name']; league=m['competition']['name']; time=m['utcDate'][11:16]
        html+=f"<div style='background:#000;padding:10px;border-radius:8px;margin:8px 0;line-height:1.5'><b>#{i} {home} vs {away}</b> <span style='color:#ffcc00'>- {time} GMT - {m['utcDate'][:10]}</span><br><small style='color:#aaa'>{league}</small><br><b style='color:{couleur}'>🎯 {res['market']} - {conf}%</b><br><small style='color:#ccc'>{res['raison']}</small><br><small style='color:#888'>{' | '.join(res['preuves'])}</small></div>"
    html+="</div>"
    return html

@app.route("/")
def home():
    force=request.args.get("force")=="1"
    today=datetime.utcnow().strftime("%Y-%m-%d")
    cached_data,cached_date=get_cache()
    if not force and cached_data and cached_date==today: return cached_data
    html="<html><head><meta name='viewport' content='width=device-width'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:10px'>"
    html+="<h2>⚽ BOSS V32 - FOOTBALL-DATA FIX</h2>"
    html+="<p style='font-size:11px;color:#ffcc00;background:#222;padding:8px;border-radius:6px'>V32 = On demande par compétitions, pas en vrac. Under/Over seulement. Aucun 100% garanti. 18+.</p>"
    if not TOKEN: return html+"<p style='color:red'>FOOTBALL_DATA_KEY manquante</p></body></html>"
    try:
        results=[]; total_scan=0; debug=""
        # 4 JOURS : aujourd'hui + 3 jours
        date_from = today
        date_to = (datetime.utcnow()+timedelta(days=3)).strftime("%Y-%m-%d")
        # METHODE 1 : avec competitions
        r=requests.get(f"{BASE}/matches", headers=HEADERS, params={"competitions":COMPS,"dateFrom":date_from,"dateTo":date_to,"status":"SCHEDULED"}, timeout=15)
        debug+=f"Appel 1: {r.status_code} | "
        if r.status_code==200:
            matches=r.json().get('matches',[])
            total_scan=len(matches)
            debug+=f"{total_scan} matchs trouvés | "
        else:
            debug+=f"Erreur: {r.text[:200]} | "
            # METHODE 2 : sans competitions
            r2=requests.get(f"{BASE}/matches", headers=HEADERS, params={"dateFrom":date_from,"dateTo":date_to}, timeout=15)
            debug+=f"Appel 2: {r2.status_code} | "
            if r2.status_code==200:
                matches=r2.json().get('matches',[])
                total_scan=len(matches)
        for m in matches[:40]:
            res=fouille(m)
            if res: results.append((res['conf'],m,res))
        results=sorted(results,key=lambda x:x[0],reverse=True)[:10]
        html+=f"<p style='color:#0f0'>🟢 {total_scan} matchs scannés | {len(results)} SAFE trouvés</p>"
        html+=f"<p style='font-size:10px;color:#888;background:#222;padding:6px;border-radius:6px'>DEBUG: {debug} Dates: {date_from} -> {date_to}</p>"
        if len(results)<3:
            html+=f"<div style='background:#2a1a1a;border:1px solid #ff4444;padding:20px;border-radius:12px;text-align:center'><h3>🚫 PAS ASSEZ DE SAFE</h3><p>{total_scan} matchs scannés, {len(results)} SAFE. Ne joue pas.</p></div>"
        else:
            html+=render_ticket("TICKET SAFE - Les 3 Supers Bons","#00ff00","🎯",results[:3],"Les 3 plus crème. Mise normale.")
            if len(results)>=5: html+=render_ticket("TICKET FUN - Les 5 Supers Bons","#ffcc00","🔥",results[:5],"Petite mise.")
            if len(results)>5: html+=render_ticket(f"TICKET JACKPOT - Les {len(results)} Bons","#ff44ff","💰",results,f"Le gros coup avec les {len(results)} SAFE. Très petite mise.")
    except Exception as e: html+=f"<p style='color:red'>Erreur: {e}</p>"
    html+="<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 FORCER ACTU - V32</a></body></html>"
    save_cache(html,today)
    return html

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
