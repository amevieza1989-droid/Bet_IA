import os, requests
from flask import Flask, render_template_string, request
from datetime import datetime, timedelta

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", "").strip()
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "6"))
CACHE = {"data": None, "time": None}

# League Cup Angleterre = ID 48 sur API-Football
LEAGUE_ID = 48
SEASON = datetime.now().year  # 2026

HTML = """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0a0a0a;color:white;font-family:Arial;padding:12px}
.card{background:#1a1a1a;border:1px solid #333;padding:12px;border-radius:10px;margin:10px 0}
.badge{background:#ffcc00;color:black;padding:4px 8px;border-radius:5px;font-weight:bold}
.btn{background:#ffcc00;color:black;width:100%;padding:15px;font-size:17px;font-weight:bold;border:none;border-radius:10px;margin-top:10px}
small{color:#aaa}
.live{color:#00ff88}
</style></head><body>
<h2>⚽ BOSS V14 - {{count}} MATCHS LIVE ODDS</h2>
<div><span class="live">● LIVE ODDS</span> | API: {{api}} | {{heure}} GMT | Cache {{cache}}h</div>
{% for m in matchs %}
<div class="card">
<span class="badge">{{m.pct}}%</span> <b>{{m.equipe1}} vs {{m.equipe2}}</b> - {{m.heure}}<br>
<b style="color:#ffcc00">{{m.prono}} @{{m.cote}}</b> {% if m.is_real %} <small style="color:#00ff88">✔ VRAIE COTE</small> {% else %} <small style="color:#ff4444">DEMO</small> {% endif %}<br>
<small>{{m.league}} | Book: {{m.bookmaker}}</small>
</div>
{% endfor %}
{% if error %}<div style="color:#ff4444;border:1px solid red;padding:10px;border-radius:8px">Erreur API: {{error}}</div>{% endif %}
<form method="POST" action="/?force=1"><button class="btn">ACTUALISER VRAIES COTES - {{date}}</button></form>
<div style="margin-top:15px"><small>Si tu vois DEMO, c'est que l'API n'a pas renvoyé de cote pour ce match. Vérifie ton crédit API-Football.</small></div>
</body></html>
"""

def get_real_odds():
    """Va chercher les vrais fixtures + cotes sur API-Football"""
    if not API_KEY:
        return None, "Pas de API_KEY"
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        headers = {"x-apisports-key": API_KEY}
        
        # 1. Fixtures du jour pour League Cup
        url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={LEAGUE_ID}&season={SEASON}&date={today}"
        r = requests.get(url_fixtures, headers=headers, timeout=15)
        data = r.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            # Si pas de match aujourd'hui, prend les prochains non commencés
            url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={LEAGUE_ID}&season={SEASON}&next=10"
            r = requests.get(url_fixtures, headers=headers, timeout=15)
            data = r.json()
            fixtures = data.get("response", [])[:5]

        result = []
        for f in fixtures[:5]:
            fid = f["fixture"]["id"]
            team1 = f["teams"]["home"]["name"]
            team2 = f["teams"]["away"]["name"]
            heure = f["fixture"]["date"][11:16] # HH:MM
            league = f["league"]["name"]

            # 2. Cotes pour ce fixture
            url_odds = f"https://v3.football.api-sports.io/odds?fixture={fid}"
            ro = requests.get(url_odds, headers=headers, timeout=15).json()
            
            cote = "1.85" # fallback
            bookmaker = "1xBet/1win (via API)"
            is_real = False
            prono = "VICTOIRE Domicile"
            
            if ro.get("response"):
                try:
                    # Prend le 1er bookmaker avec Home/Draw/Away
                    bets = ro["response"][0]["bookmakers"][0]["bets"]
                    for b in bets:
                        if b["name"] == "Match Winner":
                            values = b["values"]
                            # values = [{'value':'Home','odd':'1.66'}, ...]
                            for v in values:
                                if v["value"] == "Home":
                                    cote = v["odd"]
                                    is_real = True
                                    break
                except:
                    pass
            
            # Calcul % simple basé sur cote
            try:
                pct = int(100 / (float(cote) + 0.3))
                pct = max(60, min(85, pct))
            except:
                pct = 70

            result.append({
                "equipe1": team1, "equipe2": team2, "heure": heure,
                "cote": cote, "prono": prono, "pct": pct,
                "league": league, "bookmaker": bookmaker, "is_real": is_real
            })
        
        return result, None
    except Exception as e:
        return None, str(e)

@app.route("/", methods=["GET","POST"])
def index():
    force = request.args.get("force")=="1" or request.method=="POST"
    now = datetime.now()
    if CACHE["data"] and CACHE["time"] and not force:
        if now - CACHE["time"] < timedelta(hours=CACHE_HOURS):
            return render_template_string(HTML, **CACHE["data"])
    
    matchs, error = get_real_odds()
    
    # Fallback si API vide = tes 5 matchs d'hier mais marqués DEMO
    if not matchs:
        matchs = [
            {"equipe1":"Manchester City","equipe2":"Brighton","heure":"19:30","cote":"1.66","prono":"VICTOIRE Man City","pct":78,"league":"League Cup","bookmaker":"DEMO","is_real":False},
            {"equipe1":"Fulham","equipe2":"Crystal Palace","heure":"19:45","cote":"1.74","prono":"VICTOIRE Fulham","pct":72,"league":"League Cup","bookmaker":"DEMO","is_real":False},
            {"equipe1":"Bournemouth","equipe2":"Aston Villa","heure":"19:45","cote":"1.42","prono":"Double Chance 1X","pct":68,"league":"League Cup","bookmaker":"DEMO","is_real":False},
            {"equipe1":"Sunderland","equipe2":"Brentford","heure":"19:45","cote":"1.89","prono":"VICTOIRE Brentford","pct":75,"league":"League Cup","bookmaker":"DEMO","is_real":False},
            {"equipe1":"Liverpool","equipe2":"Chelsea","heure":"20:00","cote":"2.23","prono":"1X + BTTS","pct":70,"league":"League Cup","bookmaker":"DEMO","is_real":False},
        ]
        if not error:
            error = "API vide - Vérifie date/league ou crédit API"

    data = {
        "count": len(matchs), "api": "OUI" if API_KEY else "NON",
        "heure": now.strftime("%H:%M"), "date": now.strftime("%d/%m/%Y"),
        "matchs": matchs, "cache": CACHE_HOURS, "error": error
    }
    CACHE["data"]=data; CACHE["time"]=now
    return render_template_string(HTML, **data)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
