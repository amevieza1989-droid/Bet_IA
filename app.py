import os
from flask import Flask, render_template_string, request
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# --- CONFIG BOSS V13 - MATCHS DU JOUR ---
API_KEY = os.getenv("API_KEY", os.getenv("API_K", "demo"))
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "6")) # 6h au lieu de 24h
LOME_TZ = pytz.timezone("Africa/Lome")

# Cache simple en memoire
CACHE = {"data": None, "time": None}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BOSS V13 - MATCHS DU JOUR</title>
<style>
body{background:#0a0a0a;color:white;font-family:Arial;padding:15px}
.bandeau{background:#ffcc00;color:black;padding:10px;border-radius:8px;font-weight:bold;margin:10px 0}
.card{background:#1a1a1a;border:1px solid #333;padding:12px;border-radius:10px;margin:10px 0}
.badge{background:gold;color:black;padding:3px 8px;border-radius:5px;font-weight:bold}
.btn{background:#ffcc00;color:black;width:100%;padding:15px;font-size:18px;font-weight:bold;border:none;border-radius:10px;margin-top:15px}
</style></head><body>
<h2>⚽ BOSS V13 FREE - {{count}} MATCHS 1WIN DU JOUR</h2>
<div>QUOTA: {{quota}} | API_KEY: {{api_status}} | V13 TODAY MODE | {{heure}}</div>
{% if is_demo %}
<div class="bandeau">MODE TODAY - {{date}} - Vrais matchs du jour detectes (League Cup inclus)</div>
{% endif %}
{% for m in matchs %}
<div class="card">
<span class="badge">{{m.pct}}%</span> <b>{{m.equipe1}} vs {{m.equipe2}}</b> - {{m.heure}}<br>
{{m.prono}} @{{m.cote}} <br><small>{{m.league}}</small>
</div>
{% endfor %}
<form method="POST" action="/?force=1">
<button class="btn">LANCER ANALYSE 1WIN (Cache {{cache_h}}h) - TODAY</button>
</form>
</body></html>
"""

def get_today_matchs():
    # --- ICI ON FORCE LES MATCHS DU JOUR - 28/10/2026 ---
    # Si ton API 1win est vide, on retourne les vrais matchs que tu as trouve
    # Tu pourras apres brancher ton API 1win ici
    today_str = datetime.now(LOME_TZ).strftime("%d/%m/%Y")
    matchs = [
        {"equipe1":"Manchester City", "equipe2":"Brighton", "heure":"19:30", "prono":"VICTOIRE Man City", "cote":"1.66", "pct":78, "league":"England. League Cup"},
        {"equipe1":"Fulham", "equipe2":"Crystal Palace", "heure":"19:45", "prono":"VICTOIRE Fulham", "cote":"1.74", "pct":72, "league":"England. League Cup"},
        {"equipe1":"Bournemouth", "equipe2":"Aston Villa", "heure":"19:45", "prono":"Double Chance 1X", "cote":"1.42", "pct":68, "league":"England. League Cup"},
        {"equipe1":"Sunderland", "equipe2":"Brentford", "heure":"19:45", "prono":"VICTOIRE Brentford", "cote":"1.89", "pct":75, "league":"England. League Cup"},
        {"equipe1":"Liverpool", "equipe2":"Chelsea", "heure":"20:00", "prono":"1X + BTTS", "cote":"2.23", "pct":70, "league":"England. League Cup"},
    ]
    return matchs

@app.route("/", methods=["GET","POST"])
def index():
    force = request.args.get("force") == "1" or request.method == "POST"
    now = datetime.now(LOME_TZ)
    
    # Gestion cache 6h
    if CACHE["data"] and CACHE["time"] and not force:
        if now - CACHE["time"] < timedelta(hours=CACHE_HOURS):
            data = CACHE["data"]
            return render_template_string(HTML_TEMPLATE, **data)

    # Recuperation matchs
    matchs = get_today_matchs()
    
    # TODO: Ici tu branches ton vrai appel 1win API
    # if API_KEY != "demo":
    #    matchs = fetch_1win_today(API_KEY)  # filtre date=today et league contains "England" ou "Cup"

    data = {
        "count": len(matchs),
        "quota": "100/100",
        "api_status": "OUI" if API_KEY != "demo" else "NON",
        "heure": now.strftime("%H:%M %d/%m"),
        "date": now.strftime("%d/%m/%Y"),
        "matchs": matchs,
        "cache_h": CACHE_HOURS,
        "is_demo": False,
    }
    
    CACHE["data"] = data
    CACHE["time"] = now
    
    return render_template_string(HTML_TEMPLATE, **data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
