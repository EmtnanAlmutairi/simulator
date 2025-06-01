# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load mock stock data
with open("data/mock_stocks.json") as f:
    stocks_data = json.load(f)

portfolio = {
    "cash": 100000,
    "stocks": {},
    "history": []
}

class TradeRequest(BaseModel):
    symbol: str
    quantity: int

@app.get("/stocks")
def get_stocks():
    return stocks_data

@app.get("/wallet")
def get_wallet():
    return portfolio

@app.get("/wallet/history")
def get_history():
    return portfolio["history"]

@app.post("/wallet/buy")
def buy_stock(trade: TradeRequest):
    stock = next((s for s in stocks_data if s["symbol"] == trade.symbol), None)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    total_price = stock["price"] * trade.quantity
    if portfolio["cash"] < total_price:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    portfolio["cash"] -= total_price
    if trade.symbol in portfolio["stocks"]:
        portfolio["stocks"][trade.symbol]["quantity"] += trade.quantity
        portfolio["stocks"][trade.symbol]["total_invested"] += total_price
    else:
        portfolio["stocks"][trade.symbol] = {
            "quantity": trade.quantity,
            "total_invested": total_price
        }
    portfolio["history"].append({"action": "buy", "symbol": trade.symbol, "quantity": trade.quantity, "price": stock["price"]})
    return {"message": "Stock purchased successfully"}

@app.post("/wallet/sell")
def sell_stock(trade: TradeRequest):
    if trade.symbol not in portfolio["stocks"] or portfolio["stocks"][trade.symbol]["quantity"] < trade.quantity:
        raise HTTPException(status_code=400, detail="Not enough shares to sell")

    stock = next((s for s in stocks_data if s["symbol"] == trade.symbol), None)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    total_price = stock["price"] * trade.quantity
    portfolio["stocks"][trade.symbol]["quantity"] -= trade.quantity
    portfolio["cash"] += total_price

    if portfolio["stocks"][trade.symbol]["quantity"] == 0:
        del portfolio["stocks"][trade.symbol]

    portfolio["history"].append({"action": "sell", "symbol": trade.symbol, "quantity": trade.quantity, "price": stock["price"]})
    return {"message": "Stock sold successfully"}
