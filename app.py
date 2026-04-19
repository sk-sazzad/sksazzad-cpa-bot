from flask import Flask, request
import requests
import json

app = Flask(__name__)

# =====================================
# TELEGRAM CONFIG
# =====================================

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# =====================================
# SUPABASE CONFIG
# =====================================

SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/leads"

# =====================================
# TELEGRAM SEND FUNCTION
# =====================================

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    requests.post(url, data=payload)


# =====================================
# MAIN MENU (RESPONSIVE + SIDE BY SIDE)
# =====================================

def main_menu():
    return {
        "keyboard": [
            ["📊 Reports", "💰 Revenue"],
            ["🌐 Networks", "📈 Performance"],
            ["🌍 GEO Report", "⚙ Settings"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


# =====================================
# REPORT MENU
# =====================================

def reports_menu():
    return {
        "keyboard": [
            ["📅 Today", "📅 Yesterday"],
            ["📅 This Week", "📅 This Month"],
            ["📅 This Year", "🗓 Custom"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }


# =====================================
# REVENUE MENU
# =====================================

def revenue_menu():
    return {
        "keyboard": [
            ["💵 Today", "📅 Weekly"],
            ["🗓 Monthly", "📆 This Year"],
            ["🧾 Custom", "🏦 Lifetime"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }


# =====================================
# SETTINGS MENU
# =====================================

def settings_menu():
    return {
        "keyboard": [
            ["🕛 Daily Report Time", "📩 Approved Mode"],
            ["🔔 Alert ON/OFF", "🔄 Refresh Data"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }


# =====================================
# AUTO DETECT NETWORK BUTTONS
# =====================================

def network_menu():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    response = requests.get(
        f"{SUPABASE_TABLE_URL}?select=network",
        headers=headers
    )

    unique_networks = set()

    if response.status_code == 200:
        rows = response.json()

        for row in rows:
            if row.get("network"):
                unique_networks.add(row["network"])

    keyboard = [["🔥 All Networks"]]

    temp_row = []

    for net in sorted(unique_networks):
        temp_row.append(f"🌐 {net}")

        if len(temp_row) == 2:
            keyboard.append(temp_row)
            temp_row = []

    if temp_row:
        keyboard.append(temp_row)

    keyboard.append(["⬅ Back"])

    return {
        "keyboard": keyboard,
        "resize_keyboard": True
    }


# =====================================
# HOME ROUTE
# =====================================

@app.route("/")
def home():
    return "SK CPA Command Center Running Successfully 🚀"


# =====================================
# POSTBACK ROUTE
# =====================================

@app.route("/postback", methods=["GET", "POST"])
def postback():
    network = request.values.get("network", "Unknown")
    campaign = request.values.get("campaign", "No Campaign")
    offer_id = request.values.get("offer_id", "")
    payout = request.values.get("payout", "0")
    status = request.values.get("status", "Approved")

    subid = request.values.get("subid", "None")
    country = request.values.get("country", "Unknown")
    ip = request.values.get("ip", "N/A")
    conversion_time = request.values.get("time", "N/A")

    # =====================================
    # ONLY APPROVED ALERT TO TELEGRAM
    # =====================================

    if status.lower() == "approved" or status == "1":

        message = f"""
🚀 New CPA Lead Received

🌐 Network: {network}
🎯 Campaign: {campaign}
🆔 Offer ID: {offer_id}
💰 Payout: ${payout}
📌 Status: Approved

👤 SubID: {subid}
🌍 Country: {country}
📍 IP: {ip}
⏰ Time: {conversion_time}

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""

        send_message(CHAT_ID, message)

    # =====================================
    # SAVE TO SUPABASE
    # =====================================

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    data = {
        "network": network,
        "campaign": campaign,
        "offer_id": offer_id,
        "payout": float(payout) if payout else 0,
        "status": status,
        "subid": subid,
        "country": country,
        "ip": ip,
        "conversion_time": conversion_time
    }

    requests.post(
        SUPABASE_TABLE_URL,
        headers=headers,
        json=data
    )

    return "Postback Received + Saved Successfully ✅"


# =====================================
# WEBHOOK
# =====================================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # =====================================
    # START
    # =====================================

    if text == "/start":
        send_message(
            chat_id,
            "💎 Welcome to SK CPA Command Center 🚀",
            main_menu()
        )

    # =====================================
    # REPORTS
    # =====================================

    elif text == "📊 Reports":
        send_message(
            chat_id,
            "📊 Select Report Type",
            reports_menu()
        )

    # =====================================
    # REVENUE
    # =====================================

    elif text == "💰 Revenue":
        send_message(
            chat_id,
            "💰 Revenue Dashboard",
            revenue_menu()
        )

    # =====================================
    # NETWORKS
    # =====================================

    elif text == "🌐 Networks":
        send_message(
            chat_id,
            "🌐 Auto Detected Networks",
            network_menu()
        )

    # =====================================
    # GEO REPORT
    # =====================================

    elif text == "🌍 GEO Report":
        send_message(
            chat_id,
            """
🌍 GEO Performance

🇺🇸 USA → $120
🇬🇧 UK → $85
🇨🇦 CA → $61
🇦🇺 AU → $44

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""
        )

    # =====================================
    # SETTINGS
    # =====================================

    elif text == "⚙ Settings":
        send_message(
            chat_id,
            "⚙ Admin Settings Panel",
            settings_menu()
        )

    # =====================================
    # BACK
    # =====================================

    elif text == "⬅ Back":
        send_message(
            chat_id,
            "🏠 Main Menu",
            main_menu()
        )

    # =====================================
    # REPORT DEMO
    # =====================================

    elif "Today" in text or "Week" in text or "Month" in text or "Year" in text:
        send_message(
            chat_id,
            f"""
📊 Report Summary

Selected: {text}

🌐 Network: All Networks
💰 Revenue: $128.50
🎯 Leads: 34
✅ Approved: 21
❌ Rejected: 3
⏳ Pending: 10

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""
        )

    # =====================================
    # REVENUE DEMO
    # =====================================

    elif "Revenue" in text or "Lifetime" in text:
        send_message(
            chat_id,
            f"""
💰 Revenue Summary

Selected: {text}

Today's Revenue: $28.50
Weekly Revenue: $142.00
Monthly Revenue: $482.70
Lifetime Revenue: $8420.00

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""
        )

    # =====================================
    # DEFAULT
    # =====================================

    else:
        send_message(
            chat_id,
            "⚡ Please use menu buttons below",
            main_menu()
        )

    return "ok"


# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    app.run(debug=True)
