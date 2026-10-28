from flask import Flask, render_template_string, redirect
import os, json
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- CONFIG LOME ---
LOME_TZ = ZoneInfo("Africa/Lome")
DB_DIR = "/data" if os.path.exists("/data") else "."
QUOTA_FILE = os.path.join(DB_DIR, "quota_v12.json")
CACHE_FILE = os.path.join(DB_DIR, "cache_matchs_v12.json")

QUOTA_MAX = 100
FREE_MATCHS = 8

# DEMO d'hier que tu as vu (sera remplacé dès que API marche)
DEMO_MATCHS = [
    {"heure": "18:45", "domicile": "Roma", "exterieur": "Cagliari", "compet": "Serie A", "prono": "VICTOIRE Roma", "cote": 1.85, "pct": 82, "details": ["Domicile fort @ 1.85", "Forme: 3W sur 5", "Compo OK"], "v1": 1.85, "x": 3.60, "v2": 4.20},
    {"heure": "19:00", "domicile": "Torino", "exterieur": "Como", "compet": "Serie A", "prono": "VICTOIRE Torino", "cote": 2.1, "pct": 82, "details": ["Domicile fort", "Forme: 2W sur 5", "Compo OK"], "v1": 2.10, "x": 3.20, "v2": 3.40},
    {"heure": "19:45", "domicile": "Sassuolo", "exterieur": "Lazio", "compet": "Serie A", "prono": "VICTOIRE Lazio", "cote": 2.2, "pct": 78, "details": ["Exterieur fort", "Forme: 4W sur 5"], "v1": 2.80, "x": 3.10, "v2": 2.20},
]

def get_lome_now():
    return datetime.now(LOME_TZ)

def load_quota():
    today_str = get_lome_now().strftime('%Y-%m-%d')
    if not os.path.exists(QUOTA_FILE):
        data = {"date": today_str, "used": 0}
        save_quota(data)
        return data
    try:
        with open(QUOTA_FILE, 'r') as f:
            data = json.load(f)
        # V12.1 FIX: Si la date a changé à Lomé, on RESET auto même si serveur dormait
        if data.get("date") != today_str:
            data = {"date": today_str, "used": 0}
            save_quota(data)
        return data
    except:
        data = {"date": today_str, "used": 0}
        save_quota(data)
        return data

def save_quota(data):
    with open(QUOTA_FILE, 'w') as f:
        json.dump(data, f)

def load_cache():
    today_str = get_lome_now().strftime('%Y-%m-%d')
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
        if data.get("date") == today_str:
            return data.get("matchs")
    except:
        pass
    return None

def save_cache(matchs):
    today_str = get_lome_now().strftime('%Y-%m-%d')
    with open(CACHE_FILE, 'w') as f:
        json.dump({"date": today_str, "matchs": matchs}, f)

def fetch_api_real():
    # ICI tu mets ton vrai appel API-Football
    # Pour l'instant on simule, remplace par requests.get(...)
    # Si tu as plus de quota, cette fonction ne sera appelée qu'UNE FOIS par jour
    try:
        # Exemple: response = requests.get(...)
        # return parse_response(response)
        return None # Force DEMO si tu n'as pas mis ta clé
    except:
        return None

@app.route('/')
def home():
    quota_data = load_quota()
    used = quota_data["used"]
    reste = QUOTA_MAX - used
    today_lome = get_lome_now().strftime('%d/%m/%Y %H:%M Lomé')

    # V12.1 CACHE: On ne tape l'API qu'une fois par jour
    matchs = load_cache()
    is_demo = False

    if not matchs:
        if reste > 0:
            real = fetch_api_real()
            if real:
                matchs = real
                quota_data["used"] += 1
                save_quota(quota_data)
                save_cache(matchs)
                reste = QUOTA_MAX - quota_data["used"]
            else:
                matchs = DEMO_MATCHS
                is_demo = True
        else:
            matchs = DEMO_MATCHS
            is_demo = True

    # Calcul cote totale
    cote_tot = 1
    for m in matchs[:3]:
        cote_tot *= m["cote"]

    quota_color = "#ff3333" if reste == 0 else "#25D366"
    quota_text = f"QUOTA: {used}/{QUOTA_MAX} utilisés - Reste {reste} - Reset à 00h00 Lomé"
    stop_text = ""
    if reste == 0:
        stop_text = "⛔ STOP - Attends demain 00h00"
    
    demo_badge = "DEMO" if is_demo else f"LIVE {today_lome}"

    cards_html = ""
    for m in matchs:
        cards_html += f"""
        <div style="background:#111;border-left:4px solid gold;border-radius:12px;padding:12px;margin:10px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="font-weight:bold;font-size:16px">⚽ {m['domicile']} vs {m['exterieur']}</div>
                <span style="background:#25D366;color:#111;padding:4px 10px;border-radius:15px;font-weight:bold;font-size:12px">{m['pct']}%</span>
            </div>
            <div style="color:#888;font-size:12px;margin:4px 0">Serie A | ⏰ {m['heure']} Lomé | {demo_badge}</div>
            <div style="display:flex;gap:6px;margin:6px 0">
                <span style="background:#222;padding:4px 8px;border-radius:6px;font-size:12px">V1 {m['v1']}</span>
                <span style="background:#222;padding:4px 8px;border-radius:6px;font-size:12px">X {m['x']}</span>
                <span style="background:#222;padding:4px 8px;border-radius:6px;font-size:12px">V2 {m['v2']}</span>
            </div>
            <div style="background:gold;color:#111;padding:10px;border-radius:8px;font-weight:bold;text-align:center;margin-top:6px">
                👉 1 - {m['prono']} @{m['cote']}
            </div>
            <div style="margin-top:6px;font-size:11px;color:#aaa">
                {'<br>'.join([f"✅ {d}" for d in m['details']])}
            </div>
        </div>
        """

    html = f"""
    <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>body{{background:#000;color:#fff;font-family:Arial;padding:10px;margin:0}} .bar{{background:#222;border-radius:10px;height:12px;overflow:hidden;margin-top:6px}} .fill{{height:12px;background:{quota_color};width:{used}%}}</style>
    </head><body>
    <h2 style='color:#00ff88;text-align:center'>BOSS V12 FREE - 8 MATCHS / JOUR</h2>
    
    <div style='background:#111;border:1px solid {quota_color};padding:10px;border-radius:10px'>
        <div style='color:{quota_color};font-weight:bold;font-size:13px'>{quota_text}</div>
        <div class='bar'><div class='fill'></div></div>
        <div style='color:#ff5555;text-align:center;margin-top:6px;font-weight:bold'>{stop_text}</div>
        <div style='color:#555;font-size:10px;text-align:center;margin-top:4px'>Heure serveur Lomé: {today_lome} | Fix V12.1 Cache 24h</div>
    </div>

    <div style='background:#1a1a1a;border:1px solid gold;border-radius:12px;padding:12px;margin-top:12px'>
        <div style='font-weight:bold'>3 MATCHS - {demo_badge}<br>COTE TOT {cote_tot:.2f}</div>
        <div style='margin-top:8px;font-size:13px;color:#ccc'>
            1. {matchs[0]['heure']} - {matchs[0]['domicile']} vs {matchs[0]['exterieur']} => {matchs[0]['prono']} @{matchs[0]['v1']}<br>
            2. {matchs[1]['heure']} - {matchs[1]['domicile']} vs {matchs[1]['exterieur']} => {matchs[1]['prono']} @{matchs[1]['v1']}<br>
            3. {matchs[2]['heure']} - {matchs[2]['domicile']} vs {matchs[2]['exterieur']} => {matchs[2]['prono']} @{matchs[2]['v2']}<br>
        </div>
    </div>

    <a href='/force-refresh' style='display:block;background:gold;color:#111;padding:14px;border-radius:10px;text-align:center;text-decoration:none;font-weight:bold;margin-top:12px'>🔥 LANCER ANALYSE (Cache 24h)</a>

    {cards_html}

    <div style='text-align:center;margin-top:15px'>
        <a href='/reset-quota' style='color:#444;font-size:11px'>[ADMIN] Forcer Reset Quota</a>
    </div>
    </body></html>
    """
    return html

@app.route('/force-refresh')
def force_refresh():
    # Ne refetch que si on a du quota et que le cache est vide
    quota_data = load_quota()
    if quota_data["used"] < QUOTA_MAX:
        # Supprime cache pour forcer nouveau fetch
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    return redirect('/')

@app.route('/reset-quota')
def reset_quota():
    # Pour toi BOSS, pour débloquer à 03h33 sans attendre
    today_str = get_lome_now().strftime('%Y-%m-%d')
    save_quota({"date": today_str, "used": 0})
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
    """

Copie, déploie, et clique sur **`/reset-quota`** une fois. Ton compteur va repasser à 0/100 et tu auras les matchs du jour.

Après ça, plus jamais bloqué à 03h du mat.
