import os, requests, json
from datetime import datetime, timedelta
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.getenv("FOOTBALL_DATA_KEY","").strip()
BASE = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": TOKEN}
COMPS = "CL,EL,PL,PD,SA,BL1,FL1"

def get_team_stats(team_id):
    try:
        r = requests.get(f"{BASE}/teams/{team_id}/matches", headers=HEADERS, params={"status":"FINISHED","limit":8}, timeout=8)
        if r.status_code != 200: return None
        games = r.json().get('matches',[])
        tot=0; u35=0; o05=0; scores=[]
        for g in games:
            ft=g.get('score',{}).get('fullTime',{})
            hg=ft.get('home'); ag=ft.get('away')
            if hg is None: continue
            s=hg+ag; tot+=1; scores.append(f"{hg}-{ag}")
            if s<=3: u35+=1
            if s>=1: o05+=1
        return {'tot':tot,'u35':u35,'o05':o05,'scores':scores}
    except: return None

@app.route("/")
def home():
    html = "<html><head><meta name='viewport' content='width=device-width'><meta charset='utf-8'></head><body style='background:#0f0f0f;color:#fff;font-family:sans-serif;padding:12px'>"
    html += "<h2>⚽ BOSS V36 - ULTRA LIGHT</h2>"
    if not TOKEN: return html+"<p style='color:red'>KEY manquante</p></body></html>"

    today = datetime.utcnow().strftime("%Y-%m-%d")
    date_to = (datetime.utcnow()+timedelta(days=3)).strftime("%Y-%m-%d")
    
    try:
        # 1 SEUL APPEL = 1 seconde
        r = requests.get(f"{BASE}/matches", headers=HEADERS, params={"competitions":COMPS,"dateFrom":today,"dateTo":date_to}, timeout=10)
        if r.status_code == 429:
            return html+f"<div style='background:#222;padding:20px;border-radius:12px'><h3 style='color:#ffcc00'>⏳ Attends 1 minute</h3><p>Tu as fait trop de F5. Football-Data te bloque 1 min. Ne clique pas, attends 60 sec puis <a href='/?force=1' style='color:#ffcc00'>clique ici</a></p></div></body></html>"
        if r.status_code != 200:
            return html+f"<p style='color:red'>API {r.status_code}: {r.text[:300]}</p></body></html>"
        
        matches = [m for m in r.json().get('matches',[]) if m['status'] in ['TIMED','SCHEDULED']][:15]
        html+=f"<p style='color:#0f0;background:#111;padding:8px;border-radius:8px'>🟢 Token OK - {len(matches)} matchs trouvés | Analyse des 3 premiers seulement pour aller vite</p>"

        if not matches:
            html+="<p>Pas de matchs ces 3 jours dans CL/PL/PD/SA/BL1. C'est normal, on est mardi.</p>"
            return html+"</body></html>"

        # Analyse seulement 3 matchs pour aller vite
        found=0
        for m in matches[:3]:
            try:
                home=m['homeTeam'].get('shortName') or m['homeTeam']['name']; away=m['awayTeam'].get('shortName') or m['awayTeam']['name']; league=m['competition']['name']; t=m['utcDate'][11:16]
                h_stat = get_team_stats(m['homeTeam']['id'])
                a_stat = get_team_stats(m['awayTeam']['id'])
                if not h_stat or not a_stat: 
                    html+=f"<div style='background:#111;padding:10px;margin:10px 0;border-radius:8px'><b>{home} vs {away}</b> - {league} - {t} GMT<br><small style='color:#888'>Stats pas assez</small></div>"
                    continue
                tot = h_stat['tot']+a_stat['tot']
                if tot==0: continue
                pu35 = (h_stat['u35']+a_stat['u35'])/tot*100
                po05 = (h_stat['o05']+a_stat['o05'])/tot*100
                
                if pu35>=70:
                    found+=1
                    html+=f"<div style='background:#111;border:2px solid #00ff00;padding:12px;margin:12px 0;border-radius:12px'><b>✅ {home} vs {away}</b> <span style='color:#ffcc00'>{t}</span><br><small>{league}</small><br><b style='color:#00ff00'>🎯 UNDER 3.5 - {pu35:.0f}%</b><br><small style='color:#ccc'>{pu35:.0f}% des {tot} derniers matchs font 0-3 buts</small><br><small style='color:#888'>Derniers: {', '.join(h_stat['scores'][:4])}</small></div>"
                elif po05>=85:
                    found+=1
                    html+=f"<div style='background:#111;border:2px solid #00ff00;padding:12px;margin:12px 0;border-radius:12px'><b>✅ {home} vs {away}</b> <span style='color:#ffcc00'>{t}</span><br><small>{league}</small><br><b style='color:#00ff00'>🎯 OVER 0.5 - {po05:.0f}%</b><br><small style='color:#ccc'>{po05:.0f}% ont au moins 1 but</small></div>"
                else:
                    html+=f"<div style='background:#111;padding:10px;margin:10px 0;border-radius:8px;opacity:0.6'><b>{home} vs {away}</b> - {pu35:.0f}% UNDER 3.5 / {po05:.0f}% OVER 0.5 - pas SAFE</div>"
            except Exception as e:
                continue
        
        if found==0:
            html+=f"<p style='color:#ff4444'>0 SAFE sur les 3 premiers. Clique FORCER pour voir 3 autres.</p>"

    except Exception as e:
        html+=f"<p style='color:red'>Erreur: {e}</p>"

    html+="<br><a href='/?force=1' style='display:block;background:#ffcc00;color:#000;text-align:center;padding:16px;border-radius:10px;text-decoration:none;font-weight:bold'>🔄 VOIR 3 SUIVANTS</a></body></html>"
    return html

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
