from flask import Flask, request
import requests

app = Flask(__name__)

# Telegram Config
BOT_TOKEN = "8647704351:AAGR533RLt8K1UTDZEHNlRGX0Qr9PXzmKIo"
CHAT_ID = "5451893008"

# Supabase Config
SUPABASE_URL = "https://kpujijdgrtxkuvhljvrd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtwdWppamRncnR4a3V2aGxqdnJkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1ODQ4NDcsImV4cCI6MjA5MjE2MDg0N30.Ty-sRPph3RA-0EsIAZ_Fbg6FgkaDTVbwKztpRg4dp9s"

SUPABASE_TABLE_URL = f"{SUPABASE_URL}/rest/v1/leads"

@app.route("/")
def home():
    return "CPA Lead Tracker + Dashboard Running Successfully 🚀"

@app.route("/postback", methods=["GET", "POST"])
def postback():
    network = request.values.get("network", "Unknown")

    campaign = request.values.get("campaign") or request.values.get("offer_name") or "No Campaign"
    offer_id = request.values.get("offer_id", "")
    payout = request.values.get("payout", "0")
    status = request.values.get("status", "Pending")

    subid = request.values.get("subid") or request.values.get("tracking_id") or request.values.get("sid") or "None"
    subid2 = request.values.get("subid2", "")
    subid3 = request.values.get("subid3", "")
    subid4 = request.values.get("subid4", "")
    subid5 = request.values.get("subid5", "")

    country = request.values.get("country", "Unknown")
    ip = request.values.get("ip", "N/A")
    device = request.values.get("device", "")

    click_id = request.values.get("click_id") or request.values.get("code") or ""
    conversion_time = request.values.get("time", "N/A")

    # Telegram Message
    message = f"""
🔥 New Lead Received

Network: {network}
Campaign: {campaign}
Offer ID: {offer_id}
Payout: ${payout}
Status: {status}

SubID: {subid}
Country: {country}
IP: {ip}
Time: {conversion_time}
"""

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(telegram_url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

    # Save to Supabase
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
        "subid2": subid2,
        "subid3": subid3,
        "subid4": subid4,
        "subid5": subid5,
        "country": country,
        "ip": ip,
        "device": device,
        "click_id": click_id,
        "conversion_time": conversion_time
    }

    requests.post(SUPABASE_TABLE_URL, headers=headers, json=data)

    return "Postback Received + Saved Successfully ✅"

if __name__ == "__main__":
    app.run(debug=True)
