# =========================================
# SK CPA COMMAND CENTER — PRODUCTION READY
# Fixed: real DB reports, auth, validation,
#        error handling, live API endpoint
# =========================================

from flask import Flask, request, render_template, jsonify, Response
import requests
import json
import os
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# =====================================
# CONFIG FROM ENVIRONMENT VARIABLES
# =====================================

BOT_TOKEN       = os.environ.get("BOT_TOKEN")
CHAT_ID         = os.environ.get("CHAT_ID")
SUPABASE_URL    = os.environ.get("SUPABASE_URL")
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY")
POSTBACK_SECRET = os.environ.get("POSTBACK_SECRET", "")   # token CPA networks send
DASHBOARD_USER  = os.environ.get("DASHBOARD_USER", "admin")
DASHBOARD_PASS  = os.environ.get("DASHBOARD_PASS", "")    # leave blank to disable auth

SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/leads" if SUPABASE_URL else ""

# Startup check
for name, val in [("BOT_TOKEN", BOT_TOKEN), ("CHAT_ID", CHAT_ID),
                  ("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_KEY", SUPABASE_KEY)]:
    if not val:
        print(f"WARNING: {name} environment variable is not set")


# =====================================
# SUPABASE HELPERS (with error handling)
# =====================================

def _sb_headers(extra=None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h

def sb_get(params=""):
    """GET rows from Supabase. Returns list or [] on failure."""
    try:
        r = requests.get(
            f"{SUPABASE_TABLE_URL}{params}",
            headers=_sb_headers(),
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[Supabase GET error] {e}")
        return []

def sb_insert(data):
    """INSERT a row. Returns True on success."""
    try:
        r = requests.post(
            SUPABASE_TABLE_URL,
            headers=_sb_headers({"Prefer": "return=minimal"}),
            json=data,
            timeout=10
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[Supabase INSERT error] {e}")
        return False


# =====================================
# TELEGRAM
# =====================================

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[Telegram error] {e}")


# =====================================
# DATE RANGE HELPER
# =====================================

def date_range(period):
    """Return (start_iso, end_iso) UTC strings for a named period."""
    now = datetime.now(timezone.utc)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = now

    elif period == "yesterday":
        d     = now - timedelta(days=1)
        start = d.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        end   = d.replace(hour=23, minute=59, second=59, microsecond=0)

    elif period == "this_week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        end = now

    elif period == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now

    elif period == "this_year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now

    else:  # lifetime / fallback
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        end   = now

    return start.isoformat(), end.isoformat()


# =====================================
# REPORT BUILDER (REAL DATA)
# =====================================

def get_report_data(period="today"):
    """Query Supabase and aggregate stats for the given period."""
    start, end = date_range(period)
    rows = sb_get(
        f"?created_at=gte.{start}&created_at=lte.{end}&select=*"
    )

    total    = len(rows)
    approved = sum(1 for r in rows if str(r.get("status", "")).lower() in ("approved", "1"))
    rejected = sum(1 for r in rows if str(r.get("status", "")).lower() == "rejected")
    pending  = total - approved - rejected
    revenue  = sum(float(r.get("payout") or 0) for r in rows)

    net_rev   = {}
    offer_cnt = {}
    geo_rev   = {}

    for r in rows:
        n = r.get("network",  "Unknown")
        o = r.get("campaign", "Unknown")
        c = r.get("country",  "Unknown")
        p = float(r.get("payout") or 0)

        net_rev[n]   = net_rev.get(n, 0)   + p
        offer_cnt[o] = offer_cnt.get(o, 0) + 1
        geo_rev[c]   = geo_rev.get(c, 0)   + p

    best_network = max(net_rev,   key=net_rev.get)   if net_rev   else "N/A"
    top_offer    = max(offer_cnt, key=offer_cnt.get) if offer_cnt else "N/A"
    top_geo      = max(geo_rev,   key=geo_rev.get)   if geo_rev   else "N/A"

    return {
        "total": total, "approved": approved,
        "rejected": rejected, "pending": pending,
        "revenue": revenue,
        "best_network": best_network,
        "top_offer": top_offer,
        "top_geo": top_geo,
        "networks": net_rev,
        "geos": geo_rev,
    }

def format_report(period, d):
    labels = {
        "today": "Today", "yesterday": "Yesterday",
        "this_week": "This Week", "this_month": "This Month",
        "this_year": "This Year", "lifetime": "Lifetime",
    }
    return f"""📊 Report — {labels.get(period, period)}

🌐 Networks Active: {len(d['networks'])}
🎯 Total Leads: {d['total']}
✅ Approved: {d['approved']}
❌ Rejected: {d['rejected']}
⏳ Pending: {d['pending']}

💰 Revenue: ${d['revenue']:.2f}

🏆 Best Network: {d['best_network']}
🔥 Top Offer: {d['top_offer']}
🌍 Top GEO: {d['top_geo']}

━━━━━━━━━━━━━━━
💎 SK CPA Command Center"""


# =====================================
# GEO REPORT (REAL DATA)
# =====================================

def get_geo_report():
    rows = sb_get("?select=country,payout")
    geo  = {}

    for r in rows:
        c = r.get("country", "Unknown")
        p = float(r.get("payout") or 0)
        if c not in geo:
            geo[c] = {"leads": 0, "revenue": 0.0}
        geo[c]["leads"]   += 1
        geo[c]["revenue"] += p

    if not geo:
        return "No GEO data found yet."

    sorted_geo = sorted(geo.items(), key=lambda x: x[1]["revenue"], reverse=True)
    msg = "🌍 GEO Performance Report\n\n"

    for country, stats in sorted_geo[:5]:
        msg += f"{country} → Leads: {stats['leads']} | Revenue: ${stats['revenue']:.2f}\n"

    msg += f"\n🏆 Top GEO: {sorted_geo[0][0]}"
    msg += "\n\n━━━━━━━━━━━━━━━\n💎 SK CPA Command Center"
    return msg


# =====================================
# DAILY AUTO REPORT (REAL DATA)
# =====================================

def send_daily_report():
    data = get_report_data("today")
    send_message(CHAT_ID, format_report("today", data))


# =====================================
# SCHEDULER
# =====================================

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_report, "cron", hour=0, minute=0)
scheduler.start()


# =====================================
# MENUS
# =====================================

def main_menu():
    return {
        "keyboard": [
            ["📊 Reports",    "💰 Revenue"],
            ["🌐 Networks",   "📈 Performance"],
            ["🌍 GEO Report", "⚙ Settings"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def reports_menu():
    return {
        "keyboard": [
            ["📅 Today",     "📅 Yesterday"],
            ["📅 This Week", "📅 This Month"],
            ["📅 This Year", "🗓 Custom"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }

def revenue_menu():
    return {
        "keyboard": [
            ["💵 Today",      "📅 Weekly"],
            ["🗓 Monthly",    "📆 This Year"],
            ["🧾 Custom",     "🏦 Lifetime"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }

def settings_menu():
    return {
        "keyboard": [
            ["🕛 Daily Report Time", "📩 Approved Mode"],
            ["🔔 Alert ON/OFF",      "🔄 Refresh Data"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }

def network_menu():
    rows = sb_get("?select=network")
    unique_networks = sorted({r["network"] for r in rows if r.get("network")})

    keyboard  = [["🔥 All Networks"]]
    temp_row  = []

    for net in unique_networks:
        temp_row.append(f"🌐 {net}")
        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []
    if temp_row:
        keyboard.append(temp_row)

    keyboard.append(["⬅ Back"])
    return {"keyboard": keyboard, "resize_keyboard": True}


# =====================================
# DASHBOARD AUTH HELPER
# =====================================

def _authorized():
    if not DASHBOARD_PASS:
        return True
    auth = request.authorization
    return (auth and auth.username == DASHBOARD_USER
            and auth.password == DASHBOARD_PASS)

def _auth_required():
    return Response(
        "Login required",
        401,
        {"WWW-Authenticate": 'Basic realm="CPA Dashboard"'}
    )


# =====================================
# ROUTES
# =====================================

@app.route("/")
def home():
    return "SK CPA Command Center Running Successfully 🚀"


@app.route("/dashboard")
def dashboard():
    if not _authorized():
        return _auth_required()
    return render_template("dashboard.html")


@app.route("/api/stats")
def api_stats():
    """Live JSON endpoint consumed by dashboard.html"""
    if not _authorized():
        return jsonify({"error": "unauthorized"}), 401

    # 7-day revenue trend
    trend_labels, trend_data = [], []
    now = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        day   = now - timedelta(days=i)
        start = day.replace(hour=0,  minute=0,  second=0,  microsecond=0).isoformat()
        end   = day.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        rows  = sb_get(f"?created_at=gte.{start}&created_at=lte.{end}&select=payout")
        rev   = sum(float(r.get("payout") or 0) for r in rows)
        trend_labels.append(day.strftime("%a"))
        trend_data.append(round(rev, 2))

    # All-time rows for overview stats
    rows = sb_get("?select=*&order=created_at.desc")

    total    = len(rows)
    approved = sum(1 for r in rows if str(r.get("status", "")).lower() in ("approved", "1"))
    rejected = sum(1 for r in rows if str(r.get("status", "")).lower() == "rejected")
    pending  = total - approved - rejected
    revenue  = sum(float(r.get("payout") or 0) for r in rows)

    net_rev   = {}
    offer_cnt = {}
    geo_rev   = {}

    for r in rows:
        n = r.get("network",  "Unknown")
        o = r.get("campaign", "Unknown")
        c = r.get("country",  "Unknown")
        p = float(r.get("payout") or 0)
        net_rev[n]   = net_rev.get(n, 0)   + p
        offer_cnt[o] = offer_cnt.get(o, 0) + 1
        geo_rev[c]   = geo_rev.get(c, 0)   + p

    top_nets  = sorted(net_rev.items(),   key=lambda x: x[1], reverse=True)[:6]
    top_geos  = sorted(geo_rev.items(),   key=lambda x: x[1], reverse=True)[:5]
    top_offer = max(offer_cnt, key=offer_cnt.get) if offer_cnt else "N/A"
    best_net  = top_nets[0][0] if top_nets else "N/A"
    top_geo   = top_geos[0][0] if top_geos else "N/A"

    recent = [
        {
            "network":    r.get("network",         ""),
            "campaign":   r.get("campaign",        ""),
            "payout":     r.get("payout",          0),
            "status":     r.get("status",          ""),
            "country":    r.get("country",         ""),
            "subid":      r.get("subid",           ""),
            "created_at": r.get("created_at",      ""),
        }
        for r in rows[:10]
    ]

    return jsonify({
        "summary": {
            "revenue":      round(revenue, 2),
            "total_leads":  total,
            "approved":     approved,
            "rejected":     rejected,
            "pending":      pending,
            "best_network": best_net,
            "top_geo":      top_geo,
            "top_offer":    top_offer,
        },
        "trend":    {"labels": trend_labels, "data": trend_data},
        "networks": {
            "labels": [n[0] for n in top_nets],
            "data":   [round(n[1], 2) for n in top_nets]
        },
        "geos": {
            "labels": [g[0] for g in top_geos],
            "data":   [round(g[1], 2) for g in top_geos]
        },
        "status": {
            "labels": ["Approved", "Pending", "Rejected"],
            "data":   [approved,   pending,   rejected]
        },
        "recent": recent,
    })


@app.route("/postback", methods=["GET", "POST"])
def postback():

    # --- Token auth ---
    if POSTBACK_SECRET:
        if request.values.get("secret", "") != POSTBACK_SECRET:
            return "Unauthorized", 401

    # --- Input sanitiser ---
    def clean(key, default="", max_len=200):
        val = request.values.get(key, default)
        return str(val)[:max_len].strip()

    network         = clean("network",  "Unknown")
    campaign        = clean("campaign", "No Campaign")
    offer_id        = clean("offer_id")
    payout_raw      = clean("payout",   "0", 20)
    status          = clean("status",   "Approved")
    subid           = clean("subid",    "None")
    country         = clean("country",  "Unknown", 10)
    ip              = clean("ip",       "N/A",     45)
    conversion_time = clean("time",     "N/A",     50)

    try:
        payout = round(float(payout_raw), 4)
    except ValueError:
        payout = 0.0

    # --- Telegram alert (approved only) ---
    if status.lower() in ("approved", "1"):
        send_message(CHAT_ID, f"""🚀 New CPA Lead Received

🌐 Network: {network}
🎯 Campaign: {campaign}
🆔 Offer ID: {offer_id}
💰 Payout: ${payout:.2f}
📌 Status: Approved

👤 SubID: {subid}
🌍 Country: {country}
📍 IP: {ip}
⏰ Time: {conversion_time}

━━━━━━━━━━━━━━━
💎 SK CPA Command Center""")

    # --- Save to Supabase ---
    sb_insert({
        "network":         network,
        "campaign":        campaign,
        "offer_id":        offer_id,
        "payout":          payout,
        "status":          status,
        "subid":           subid,
        "country":         country,
        "ip":              ip,
        "conversion_time": conversion_time,
    })

    return "Postback Received + Saved Successfully ✅"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text    = data["message"].get("text", "")

    # Exact period map — no loose substring matching
    period_map = {
        "📅 Today":      "today",
        "📅 Yesterday":  "yesterday",
        "📅 This Week":  "this_week",
        "📅 This Month": "this_month",
        "📅 This Year":  "this_year",
        "💵 Today":      "today",
        "📅 Weekly":     "this_week",
        "🗓 Monthly":    "this_month",
        "📆 This Year":  "this_year",
        "🧾 Custom":     "this_month",
        "🗓 Custom":     "this_month",
        "🏦 Lifetime":   "lifetime",
    }

    if text == "/start":
        send_message(chat_id, "💎 Welcome to SK CPA Command Center 🚀", main_menu())

    elif text == "📊 Reports":
        send_message(chat_id, "📊 Select Report Type", reports_menu())

    elif text == "💰 Revenue":
        send_message(chat_id, "💰 Revenue Dashboard", revenue_menu())

    elif text == "🌐 Networks":
        send_message(chat_id, "🌐 Auto Detected Networks", network_menu())

    elif text == "🌍 GEO Report":
        send_message(chat_id, get_geo_report())

    elif text == "⚙ Settings":
        send_message(chat_id, "⚙ Admin Settings Panel", settings_menu())

    elif text in period_map:
        send_message(chat_id, "⏳ Fetching data, please wait...")
        report_data = get_report_data(period_map[text])
        send_message(chat_id, format_report(period_map[text], report_data))

    elif text == "🔥 All Networks":
        send_message(chat_id, "⏳ Fetching data, please wait...")
        report_data = get_report_data("lifetime")
        send_message(chat_id, format_report("lifetime", report_data))

    elif text.startswith("🌐 "):
        # Per-network report
        network_name = text[2:].strip()
        send_message(chat_id, f"⏳ Fetching data for {network_name}...")
        start, end = date_range("lifetime")
        rows = sb_get(f"?network=eq.{requests.utils.quote(network_name)}&select=*")
        total   = len(rows)
        rev     = sum(float(r.get("payout") or 0) for r in rows)
        app_cnt = sum(1 for r in rows if str(r.get("status","")).lower() in ("approved","1"))
        send_message(chat_id, f"""🌐 Network: {network_name}

🎯 Total Leads: {total}
✅ Approved: {app_cnt}
💰 Revenue: ${rev:.2f}

━━━━━━━━━━━━━━━
💎 SK CPA Command Center""")

    elif text in ("🕛 Daily Report Time", "📩 Approved Mode",
                  "🔔 Alert ON/OFF", "🔄 Refresh Data"):
        send_message(chat_id, "⚙ Settings are managed via environment variables on your server.")

    elif text == "⬅ Back":
        send_message(chat_id, "🏠 Main Menu", main_menu())

    else:
        send_message(chat_id, "⚡ Please use the menu buttons below.", main_menu())

    return "ok"


# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    app.run()
