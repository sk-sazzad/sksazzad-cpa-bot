from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = "8647704351:AAGR533RLt8K1UTDZEHNlRGX0Qr9PXzmKIo"
CHAT_ID = "5451893008"

@app.route("/")
def home():
    return "CPA Lead Tracker Running Successfully"

@app.route("/postback")
def postback():
    network = request.args.get("network", "Unknown")
    campaign = request.args.get("campaign", "No Campaign")
    payout = request.args.get("payout", "0")
    country = request.args.get("country", "Unknown")
    subid = request.args.get("subid", "None")
    ip = request.args.get("ip", "N/A")
    time = request.args.get("time", "N/A")

    message = f"""
🔥 New Lead Received

Network: {network}
Campaign: {campaign}
Payout: ${payout}
Country: {country}
SubID: {subid}
IP: {ip}
Time: {time}
"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

    return "Postback Received Successfully"

if __name__ == "__main__":
    app.run(debug=True)
