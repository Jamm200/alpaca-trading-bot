from flask import Flask, request, jsonify
from flask_cors import CORS
import alpaca_trade_api as tradeapi
import os
import json

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return "🟢 Webhook is live!"

# === Alpaca Setup ===
API_KEY = "PK0ZSVAY9DKNL7SU8C7C"
API_SECRET = "xlf6FxklMo4wNM2fAWMRGDQkVett6OQ5pCswhQvb"
BASE_URL = "https://paper-api.alpaca.markets"
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL)

POSITION_FILE = "positions.json"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📩 Received alert:", data)

        action = data.get("action")
        side = data.get("side")
        symbol = data.get("symbol")
        qty = float(data.get("qty"))

        if action not in ["entry", "exit"]:
            return jsonify({"error": "Invalid action"}), 400

        if action == "entry":
            print(f"🚀 Placing ENTRY order: {side.upper()} {qty} {symbol}")
            order = api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type="market",
                time_in_force="gtc"
            )

            # 🔄 Try to get the latest trade price with fallback
            try:
                last_trade = api.get_latest_trade(symbol)
                last_trade_price = float(last_trade.price)
            except Exception as e:
                print("⚠️ Could not fetch latest trade. Using 0 as fallback:", e)
                last_trade_price = 0.0

            # 📝 Save position to file
            position_data = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "entry_price": last_trade_price
            }
            with open(POSITION_FILE, "w") as f:
                json.dump(position_data, f)
            print("📝 Position saved to file:", position_data)

            return jsonify({"status": "entry order sent", "order_id": order.id}), 200

        elif action == "exit":
            try:
                # ✅ Check live Alpaca position before exiting
                position = api.get_position(symbol)
                open_qty = float(position.qty)
                if open_qty > 0:
                    print(f"✅ Open position detected: {open_qty} {symbol}. Sending EXIT order.")

                    order = api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side=side,
                        type="market",
                        time_in_force="gtc"
                    )

                    if os.path.exists(POSITION_FILE):
                        os.remove(POSITION_FILE)
                        print("🧹 Position file removed on exit")

                    return jsonify({"status": "exit order sent", "order_id": order.id}), 200
                else:
                    msg = f"⚠️ No open position found for {symbol}. Exit ignored."
                    print(msg)
                    return jsonify({"status": "ignored", "message": msg}), 200

            except tradeapi.rest.APIError as e:
                if "position does not exist" in str(e):
                    msg = f"⚠️ No position exists on Alpaca for {symbol}. Exit ignored."
                    print(msg)
                    return jsonify({"status": "ignored", "message": msg}), 200
                else:
                    print("❌ API error when checking position:", e)
                    return jsonify({"error": str(e)}), 500

    except Exception as e:
        print("❌ General error:", e)
        return jsonify({
            "error": str(e),
            "troubleshooting": "Check if API keys are correct, Alpaca service is reachable, and the alert payload format is valid."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # 5000 fallback for local testing
    app.run(debug=True, host="0.0.0.0", port=port)
