import os
from flask import Flask, render_template_string, request
from datetime import datetime, timedelta

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", os.getenv("API_K", "demo"))
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "6"))
CACHE = {"data": None, "time": None}

HTML = """<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#0a0a0a;color:white;font-family:Arial;padding:15px}
.card{background:#1a1a1a;border:1px solid #333;padding:12px;border-radius:10px;margin:10px 0}
.badge{background:gold;color:black;padding:3px 8px;border-radius:5px;font-weight:bold}
.btn{background:#ffcc00;color:black;width:100%;padding:15px;font-size:18px;font-weight:bold;border:none;border-radius:10px}</style></head><body>
<h2>⚽ BOSS V13.1 - {{count}} MATCHS DU JOUR</h2>
<div>API: {{api}} | Cache {{cache}}h | {{heure}}</div>
{% for m in matchs %}<div class="card"><span class="badge">{{m.pct}}%</span> <b>{{m.equipe1}} vs {{m.equipe2}}</b> - {{m.heure}}<br>{{m.prono}} @{{m.cote}}<br><small>{{m.league}}</small></div>{% endfor %}
<form method="POST" action="/?force=1"><button class="btn">LANCER ANALYSE TODAY - {{date}}</button></form></body></html>"""

def get_matchs():
    return [
        {"equipe1":"Manchester City","equipe2":"Brighton","heure":"19:30","prono":"VICTOIRE Man City","cote":"1.66","pct":78,"league":"England. League Cup"},
        {"equipe1":"Fulham","equipe2":"Crystal Palace","heure":"19:45","prono":"VICTOIRE Fulham","cote":"1.74","pct":72,"league":"England. League Cup"},
        {"equipe1":"Bournemouth","equipe2":"Aston Villa","heure":"19:45","prono":"Double Chance 1X","cote":"1.42","pct":68,"league":"England. League Cup"},
        {"equipe1":"Sunderland","equipe2":"Brentford","heure":"19:45","prono":"VICTOIRE Brentford","cote":"1.89","pct":75,"league":"England. League Cup"},
        {"equipe1":"Liverpool","equipe2":"Chelsea","heure":"20:00","prono":"1X + BTTS","cote":"2.23","pct":70,"league":"England. League Cup"},
    ]

@app.route("/", methods=["GET","POST"])
def index():
    force = request.args.get("force")=="1" or request.method=="POST"
    now = datetime.now()
    if CACHE["data"] and CACHE["time"] and not force:
        if now - CACHE["time"] < timedelta(hours=CACHE_HOURS):
            return render_template_string(HTML, **CACHE["data"])
    matchs = get_matchs()
    data = {"count":len(matchs),"api":"OUI" if API_KEY!="demo" else "NON","heure":now.strftime("%H:%M"),"date":now.strftime("%d/%m/%Y"),"matchs":matchs,"cache":CACHE_HOURS}
    CACHE["data"]=data; CACHE["time"]=now
    return render_template_string(HTML, **data)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
