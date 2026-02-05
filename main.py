import requests
from polytools import GetQuarterEpoch
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import websockets
import asyncio
import threading

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

currency = "BTC"
c_price = 0

def GetMarkets(limit=10, active=True, API=GAMMA_API):
    response = requests.get(f"{API}/markets?active={active}")
    markets = response.json()
    return markets

class CurrentFifteenMinCrypto():
    def __init__(self, currency="btc"):
        self.currency = currency.lower()
        self.market = requests.get(f"{GAMMA_API}/markets?slug={self.currency}-updown-15m-{GetQuarterEpoch()}").json()[0]
        print("[+] Successfully got the market token ID")

    def query(self, field):
        return self.market.get(field)

    def LoadTokenIds(self):
        self.yes, self.no = json.loads(self.query("clobTokenIds"))
        print("[+] Successfully got the bets' token IDs")

    def GetPrice(self, type="yes", side="buy"):
        if type == "yes":
            token = self.yes
        else:
            token = self.no
        response = requests.get(f"https://clob.polymarket.com/price?token_id={token}&side={side}").json()
        return float(response["price"])

    def GetOrderBook(self, token_type="yes"):
        if token_type == "yes":
            token = self.yes
        else:
            token = self.no
        response = requests.get(f"https://clob.polymarket.com/book?token_id={token}").json()

        for i in range(len(response["bids"])):
            response["neg_risk"] = response["neg_risk"] == "true"
            response["bids"][i]["price"] = float(response["bids"][i]["price"])
            response["bids"][i]["size"] = float(response["bids"][i]["size"])
            response["asks"][i]["price"] = float(response["asks"][i]["price"])
            response["asks"][i]["size"] = float(response["asks"][i]["size"])
        return response

class Visualization():
    def __init__(self, market, max_points=100):
        self.yes_prices = deque(maxlen=max_points)
        self.no_prices = deque(maxlen=max_points)
        self.crypto_prices = deque(maxlen=max_points)
        self.times = deque([], maxlen=max_points)

        self.counter = 0
        self.market = market

        self.fig, self.ax = plt.subplots()
        self.line_yes, = self.ax.plot([], [], lw=2, color="green", label="Yes")
        self.line_no, = self.ax.plot([], [], lw=2, color="red", label="No")
        self.line_crypto, = self.ax.plot([], [], lw=2, color="blue", label=self.market.currency.upper())

        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Price")
        self.ax.legend()
        self.ax.set_ylim(0, 1)

    def update(self, frame):
        self.counter += 1
        yes_price = self.market.GetPrice(type="yes", side="sell")
        no_price = self.market.GetPrice(type="no", side="sell")

        self.yes_prices.append(yes_price)
        self.no_prices.append(no_price)
        if c_price == 0:
            self.crypto_prices.append(0.5)
        else:
            self.crypto_prices.append(c_price)
        self.times.append(self.counter)

        self.ax.set_title(f"Yes: {yes_price}       No: {no_price}")
        self.line_yes.set_data(list(self.times), list(self.yes_prices))
        self.line_no.set_data(list(self.times), list(self.no_prices))
        self.line_crypto.set_data(list(self.times), list(self.crypto_prices))

        if len(self.times) > 1:
            x_min, x_max = min(self.times), max(self.times)
            x_padding = max(1, (x_max - x_min) * 0.05)
            self.ax.set_xlim(x_min - x_padding, x_max + x_padding)

        return self.line

    def show(self):
        ani = animation.FuncAnimation(self.fig, self.update, interval=10, cache_frame_data=False)
        plt.show()

async def listen_btc_price(currency):
    global c_price
    BINANCE_WS = "wss://stream.binance.com/stream"
    SUBSCRIBE_MSG = {
        "method": "SUBSCRIBE",
        "params": [
            f"{currency}usdt@aggTrade"
        ],
        "id": 1
    }
    async with websockets.connect(BINANCE_WS) as ws:
        await ws.send(json.dumps(SUBSCRIBE_MSG))
        print(f"[+] Successfully subscribed to {currency.upper()}USDT aggTrade")
        base_price = 0

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if "stream" not in data:
                continue

            stream = data["stream"]
            payload = data["data"]

            if stream == f"{currency}usdt@aggTrade":
                curr_price = float(payload["p"])
                if base_price == 0:
                    base_price = curr_price
                else:
                    c_price = (100 - (base_price / curr_price) * 100) * 5 + 0.5

def start_ws():
    asyncio.run(listen_btc_price(crypto_current.currency))

crypto_current = CurrentFifteenMinCrypto(currency)
crypto_current.LoadTokenIds()

ws_thread = threading.Thread(target=start_ws, daemon=True)
ws_thread.start()

visualize = Visualization(crypto_current)
visualize.show()