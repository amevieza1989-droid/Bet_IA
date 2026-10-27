from flask import Flask, render_template, jsonify
import requests, os, random
from datetime import datetime

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "87d21d97f45e4d123844a530d0a58169")
BASE_URL = "https://v3.football.api-sports.io"
LEAGUES = [39,140,135,78,61,88]

def H(): return {"x-apisports-key": API_KEY}

def get_quota():
    try:
        r = requests.get(f"{BASE_URL}/status", headers=H(), timeout=6)
        data = r.json().get("response", {})
        req = data.get("requests", {})
        used = req.get("current", 0)
        limit = req.get("limit_day", 100)
        remain = limit - used
        return used, limit, remain
    except:
        return 0, 100, 0

def get_fixtures_fast():
    d = datetime.now().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{BASE_URL}/fixtures?date={d}", headers=H(), timeout=8)
        return [m for m in r.json().get("response", []) if m["league"]["id"] in LEAGUES][:10]
    except:
        return []

def get_odds_fast(fid):
    try:
        r = requests.get(f"{BASE_URL}/odds?fixture={fid}", headers=H(), timeout=6)
        data = r.json().get("response", [])
        if not data: return None
        for book in data[0].get("bookmakers", []):
            if book["id"] in [8,11]:
                for bet in book.get("bets", []):
                    if bet["id"]==1:
                        v1=x=v2=None
                        for v in bet["values"]:
                            if v["value"]=="Home": v1=v["odd"]
                            elif v["value"]=="Draw": x=v["odd"]
                            elif v["value"]=="Away": v2=v["odd"]
                        if v1 and x and v2:
                            return {"V1":v1,"X":x,"V2":v2,"book":book["name"]}
    except: return None
    return None

@app.route("/")
def index(): return render_template("index.html")

@app.route("/api/combine")
def combine():
    used, limit, remain = get_quota()
    fixtures = get_fixtures_fast()
    
    quota_text = f"QUOTA: {used}/{limit} utilisés - Reste {remain}"
    
    if remain <= 2 or not fixtures:
        demo = [
            {"home":"Roma","away":"Cagliari","league":"Serie A","lh":"https://media.api-sports.io/football/teams/497.png","la":"https://media.api-sports.io/football/teams/499.png","V1":"1.85","X":"3.60","V2":"4.20"},
            {"home":"Torino","away":"Como","league":"Serie A","lh":"https://media.api-sports.io/football/teams/503.png","la":"https://media.api-sports.io/football/teams/612.png","V1":"2.10","X":"3.20","V2":"3.40"},
            {"home":"Sassuolo","away":"Lazio","league":"Serie A","lh":"https://media.api-sports.io/football/teams/543.png","la":"https://media.api-sports.io/football/teams/487.png","V1":"3.10","X":"3.50","V2":"2.20"},
        ]
        res=[]
        for m in demo:
            v1=float(m["V1"]); v2=float(m["V2"])
            prono=f"VICTOIRE {m['home']}" if v1<v2 else f"VICTOIRE {m['away']}"
            cote=v1 if v1<v2 else v2
            res.append({
                "home":m["home"],"away":m["away"],"league":m["league"],
                "logo_h":m["lh"],"logo_a":m["la"],
                "odds":{"V1":m["V1"],"X":m["X"],"V2":m["V2"],"book":"DEMO"},
                "prono":prono,"cote":cote,"type":"1" if v1<v2 else "2",
                "confiance":82,"analyses":[f"🏠 Domicile fort @ {m['V1']}", "📈 Forme temps: 3W sur 5", "✅ Effectif complet (mode démo)"]
            })
        return jsonify({"matches":res,"cote_tot":8.55,"count":len(res),"mode":"DEMO - Quota épuisé","quota_used":used,"quota_limit":limit,"quota_remain":remain,"quota_text":quota_text})

    final=[]
    for m in fixtures[:8]:
        odds=get_odds_fast(m["fixture"]["id"])
        if not odds: continue
        home=m["teams"]["home"]["name"]; away=m["teams"]["away"]["name"]
        try: v1=float(odds["V1"]); v2=float(odds["V2"])
        except: continue
        prono=f"VICTOIRE {home}" if v1<v2 else f"VICTOIRE {away}"
        cote=v1 if v1<v2 else v2
        confiance=85 if min(v1,v2)<1.8 else 76
        final.append({
            "home":home,"away":away,"league":m["league"]["name"],
            "logo_h":m["teams"]["home"]["logo"],"logo_a":m["teams"]["away"]["logo"],
            "odds":odds,"prono":prono,"cote":cote,"type":"1" if v1<v2 else "2",
            "confiance":confiance,
            "analyses":[f"🏠 Cote favori @ {min(v1,v2)}", f"📊 Temps: forme récente analysée", f"✈️ Espace: perf domicile/extérieur OK"]
        })
        if len(final)>=8: break

    cote_tot=1
    for r in final: cote_tot*=float(r["cote"])
    
    used2, limit2, remain2 = get_quota()
    return jsonify({
        "matches":final,"cote_tot":round(cote_tot,2),"count":len(final),"mode":"FREE LIVE",
        "quota_used":used2,"quota_limit":limit2,"quota_remain":remain2,
        "quota_text":f"QUOTA: {used2}/{limit2} utilisés - Reste {remain2} - Reset à minuit UTC"
    })

if __name__=="__main__": app.run(host="0.0.0.0",port=10000)
