from flask import Flask, request
import requests
import json

app = Flask(__name__)

# =========================
# TELEGRAM CONFIG
# =========================

BOT_TOKEN = "8647704351:AAGR533RLt8K1UTDZEHNlRGX0Qr9PXzmKIo"
CHAT_ID = "5451893008"

# =========================
# SUPABASE CONFIG
# =========================

SUPABASE_URL = "https://kpujijdgrtxkuvhljvrd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtwdWppamRncnR4a3V2aGxqdnJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1ODQ4NDcsImV4cCI6MjA5MjE2MDg0N30.Ty-sRPph3RA-0EsIAZ_Fbg6FgkaDTVbwKztpRg4dp9s"

SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/leads"

# =========================
# TELEGRAM SEND FUNCTION
# =========================

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    requests.post(url, data=payload)


# =========================
# MAIN MENU BUTTONS
# =========================

def main_menu():
    return {
        "keyboard": [
            ["📊 Reports", "💰 Revenue"],
            ["🌐 Networks", "📈 Performance"],
            ["⚙ Settings"]
        ],
        "resize_keyboard": True
    }


def revenue_menu():
    return {
        "keyboard": [
            ["💵 Today's Revenue"],
            ["📅 Weekly Revenue"],
            ["🗓 Monthly Revenue"],
            ["📆 This Year"],
            ["🧾 Custom Range"],
            ["🏦 Total Lifetime Revenue"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }


def reports_menu():
    return {
        "keyboard": [
            ["📅 Today"],
            ["📅 Yesterday"],
            ["📅 This Week"],
            ["📅 This Month"],
            ["📅 This Year"],
            ["🗓 Custom Range"],
            ["⬅ Back"]
        ],
        "resize_keyboard": True
    }


def get_network_buttons():
    """
    Auto Detect Networks from Supabase
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    url = f"{SUPABASE_TABLE_URL}?select=network"

    response = requests.get(url, headers=headers)

    network_names = set()

    if response.status_code == 200:
        data = response.json()
        for row in data:
            if row.get("network"):
                network_names.add(row["network"])

    keyboard = [["🔥 All Networks"]]

    for network in sorted(network_names):
        keyboard.append([f"🌐 {network}"])

    keyboard.append(["⬅ Back"])

    return {
        "keyboard": keyboard,
        "resize_keyboard": True
    }


# =========================
# HOME ROUTE
# =========================

@app.route("/")
def home():
    return "SK CPA Command Center Running Successfully 🚀"


# =========================
# POSTBACK ROUTE
# =========================

@app.route("/postback", methods=["GET", "POST"])
def postback():
    network = request.values.get("network", "Unknown")

    campaign = request.values.get("campaign") or request.values.get("offer_name") or "No Campaign"
    offer_id = request.values.get("offer_id", "")
    payout = request.values.get("payout", "0")
    status = request.values.get("status", "Approved")

    subid = request.values.get("subid") or request.values.get("tracking_id") or request.values.get("sid") or "None"

    country = request.values.get("country", "Unknown")
    ip = request.values.get("ip", "N/A")
    conversion_time = request.values.get("time", "N/A")

    # =========================
    # TELEGRAM ALERT ONLY IF APPROVED
    # =========================

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

    # =========================
    # SAVE TO SUPABASE
    # =========================

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


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    # =========================
    # START
    # =========================

    if text == "/start":
        send_message(
            chat_id,
            "💎 Welcome to SK CPA Command Center 🚀",
            main_menu()
        )

    # =========================
    # REPORTS
    # =========================

    elif text == "📊 Reports":
        send_message(
            chat_id,
            "📊 Select Report Type",
            reports_menu()
        )

    # =========================
    # REVENUE
    # =========================

    elif text == "💰 Revenue":
        send_message(
            chat_id,
            "💰 Revenue Dashboard",
            revenue_menu()
        )

    # =========================
    # NETWORKS
    # =========================

    elif text == "🌐 Networks":
        send_message(
            chat_id,
            "🌐 Auto Detected Networks",
            get_network_buttons()
        )

    # =========================
    # BACK BUTTON
    # =========================

    elif text == "⬅ Back":
        send_message(
            chat_id,
            "🏠 Main Menu",
            main_menu()
        )

    # =========================
    # SIMPLE DEMO RESPONSE
    # =========================

    elif "Revenue" in text:
        send_message(
            chat_id,
            f"""
💰 Revenue Summary

Selected: {text}

This section will show:
✅ Total Revenue
✅ Leads Count
✅ Best Offer
✅ Best Network

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""
        )

    elif "Today" in text or "Week" in text or "Month" in text:
        send_message(
            chat_id,
            f"""
📊 Report Summary

Selected: {text}

🌐 Network: All Networks
💰 Revenue: $128.50
🎯 Leads: 34
✅ Approved: 21

━━━━━━━━━━━━━━━
💎 SK CPA Command Center
"""
        )

    else:
        send_message(
            chat_id,
            "⚡ Use Menu Buttons Below",
            main_menu()
        )

    return "ok"


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)
