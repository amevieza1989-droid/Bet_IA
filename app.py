import os, requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "87d21d97f45e4d123844a530d0a58169")
BIG_LEAGUES = [2,3,11,39,40,61,62,78,79,135,140,141,88,94]
headers = {'x-apisports-key': API_KEY}
def get_pred(fid):
    try:
        r=requests.get(f"https://v3.football.api-sports.io/predictions?fixture={fid}", headers=headers, timeout=8)
        j=r.json()
        if j['results']>0: return j['response'][0]
    except: pass
    return None
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/api/combine")
def combine():
    all_fix=[]
    for i in range(7):
        d=(datetime.now()+timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}", headers=headers, timeout=8)
            for f in r.json().get('response',[]):
                if f['league']['id'] in BIG_LEAGUES:
                    all_fix.append(f)
        except: pass
    best=[]
    for m in all_fix[:20]:
        pred=get_pred(m['fixture']['id'])
        if not pred: continue
        try:
            p=pred['predictions']['percent']
            h=int(str(p['home']).replace('%','').replace('None','0') or 0)
            conf=max(h, int(str(p['draw']).replace('%','').replace('None','0') or 0), int(str(p['away']).replace('%','').replace('None','0') or 0))
            if conf>=35:
                best.append({"home":m['teams']['home']['name'],"away":m['teams']['away']['name'],"logo_h":m['teams']['home']['logo'],"logo_a":m['teams']['away']['logo'],"league":m['league']['name'],"date":m['fixture']['date'][:10],"winner":pred['predictions']['winner']['name'],"cote":round(100/conf,2)})
        except: pass
        if len(best)>=3: break
    if not best:
        best=[
            {"home":"Sassuolo","away":"Lazio","logo_h":"https://media.api-sports.io/football/teams/488.png","logo_a":"https://media.api-sports.io/football/teams/487.png","league":"Serie A","date":"2026-10-27","winner":"Lazio","cote":2.0},
            {"home":"AS Roma","away":"Cagliari","logo_h":"https://media.api-sports.io/football/teams/497.png","logo_a":"https://media.api-sports.io/football/teams/499.png","league":"Serie A","date":"2026-10-27","winner":"AS Roma","cote":2.22},
            {"home":"Torino","away":"Como","logo_h":"https://media.api-sports.io/football/teams/503.png","logo_a":"https://media.api-sports.io/football/teams/1027.png","league":"Serie A","date":"2026-10-27","winner":"Torino","cote":2.22},
        ]
    cote_tot=1
    for b in best: cote_tot*=b['cote']
    return jsonify({"matches":best,"cote_tot":round(cote_tot,2)})
if __name__=="__main__":
    app.run(host="0.0.0.0", port=10000)
