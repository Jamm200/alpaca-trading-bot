import websocket
import json
import os
import alpaca_trade_api as tradeapi

API_KEY = "PKC54XX8LZYGCPCLWF2M"
API_SECRET = "D6TexlfllS1rahIqMO91tFURVf6YBlh7vFYwnOdC"
BASE_URL = "https://paper-api.alpaca.markets"
POSITION_FILE = "positions.json"
DRAWDOWN_THRESHOLD = 0.04  # 4%

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL)

def load_position():
    if os.path.exists(POSITION_FILE):
        with open(POSITION_FILE, "r") as f:
            return json.load(f)
    return None

def on_message(ws, message):
    position = load_position()
    if not position:
        return  # No position to monitor

    msg = json.loads(message)
    for item in msg:
        if item.get("T") == "t":  # trade message
            current_price = item["p"]
            print(f"📈 {position['symbol']} live price: {current_price}")

            entry_price = position["entry_price"]
            side = position["side"]
            qty = position["qty"]
            symbol = position["symbol"]

            drawdown = (entry_price - current_price) / entry_price if side == "buy" else (current_price - entry_price) / entry_price

            if drawdown >= DRAWDOWN_THRESHOLD:
                print(f"❗ Drawdown of {drawdown*100:.2f}% hit — exiting position")
                exit_side = "sell" if side == "buy" else "buy"
                try:
                    api.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side=exit_side,
                        type="market",
                        time_in_force="gtc"
                    )
                    print("✅ Emergency exit order sent")
                    os.remove(POSITION_FILE)
                    print("🧹 Position file removed after emergency exit")
                except Exception as e:
                    print(f"❌ Failed to send emergency exit: {e}")

def on_open(ws):
    print("✅ WebSocket connected")
    position = load_position()
    if position:
        ws.send(json.dumps({
            "action": "auth",
            "key": API_KEY,
            "secret": API_SECRET
        }))
        ws.send(json.dumps({
            "action": "subscribe",
            "trades": [position["symbol"]]
        }))
    else:
        print("⚠️ No open position to monitor — closing socket")
        ws.close()

def on_error(ws, error):
    print("❌ WebSocket error:", error)

def on_close(ws, code, reason):
    print("🔌 WebSocket closed:", code, reason)

if __name__ == "__main__":
    socket_url = "wss://stream.data.alpaca.markets/v2/iex"
    ws = websocket.WebSocketApp(socket_url,
                                 on_open=on_open,
                                 on_message=on_message,
                                 on_error=on_error,
                                 on_close=on_close)
    ws.run_forever()
