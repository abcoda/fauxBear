from cs50 import SQL

db = SQL("sqlite:///finance.db")
# subs = db.execute("SELECT * FROM transactions WHERE user_id = '6'")

# stocks = dict()
# for sub in subs:
#     if sub["symbol"] not in stocks:
#         stocks[sub["symbol"]] = 0
#     stocks[sub["symbol"]] += sub["shares"]

# for symbol, share in stocks.items():
#     print(symbol, share)

user_transactions = db.execute("SELECT * FROM transactions WHERE user_id = '6'")

shares = dict()
names = dict()
prices = dict()
for transaction in user_transactions:
    if transaction["symbol"] not in shares:
        shares[transaction["symbol"]] = 0
        names[transaction["symbol"]] = "test"
        #prices[transaction["symbol"]] = lookup(request.form.get("symbol")["price"]
    shares[transaction["symbol"]] += transaction["shares"]

print(names)