# export API_KEY=pk_9b5cce9a48394ba2af796af0852ceeb2
import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    user_transactions = db.execute("SELECT * FROM transactions WHERE user_id = :id", id=session["user_id"])
    stock_total = 0
    stocks = []
    shares = dict()

    for transaction in user_transactions:
        if transaction["symbol"] not in [x[0] for x in stocks]:
            shares[transaction["symbol"]] = 0
            stocks.append([transaction["symbol"], (lookup(transaction["symbol"]))[
                "name"], 0, float((lookup(transaction["symbol"]))["price"])])
        shares[transaction["symbol"]] += transaction["shares"]
    for stock in stocks:
        stock[2] = shares[stock[0]]
        stock_total += (stock[2] * stock[3])
        stock.append(usd(stock[2] * stock[3]))

    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])[0]['cash']
    total = cash + stock_total
    return render_template("index.html", stocks=stocks, cash=usd(cash), total=usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        quote = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")
        if shares[0] in ('-', '+'):
            integer = shares[1:].isdigit()
        else:
            integer = shares.isdigit()
        if not integer:
            return apology("Invalid number of shares", 400)
        if quote:
            if int(request.form.get("shares")) < 1:
                return apology("Invalid number of shares", 400)
            else:
                cost = int(request.form.get("shares")) * float(quote["price"])
                balance = db.execute("SELECT cash FROM 'users' WHERE id = :user_id", user_id=session['user_id'])[0]['cash']
                if balance >= cost:
                    balance = balance - cost
                    db.execute("UPDATE users SET cash = :balance WHERE id = :user_id", user_id=session['user_id'], balance=balance)
                    db.execute("INSERT INTO transactions ('user_id','symbol','price','shares','time') VALUES (:user_id, :symbol, :price, :shares, :datetime)",
                               user_id=session['user_id'], symbol=quote["symbol"], price=float(quote["price"]), shares=int(request.form.get("shares")), datetime=str(datetime.now()))
                    return redirect("/")
                else:
                    return apology("Insufficient funds", 400)
        else:
            return apology("Invalid Symbol", 400)
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get("username")
    if len(db.execute("SELECT * FROM users WHERE username = :username", username=username)) != 0:
        return jsonify(False)
    else:
        return jsonify(True)


@app.route("/history")
@login_required
def history():
    transactions = []
    user_transactions = db.execute("SELECT * FROM transactions WHERE user_id = :id ORDER BY time DESC", id=session["user_id"])
    for transaction in user_transactions:
        transactions.append([transaction["symbol"], transaction["shares"], transaction["price"], transaction["time"]])
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Enter a symbol", 400)
        quote = lookup(request.form.get("symbol"))
        if quote:
            return render_template("quoted.html", name=quote["name"], symbol=quote["symbol"], cost=usd(float(quote["price"])))
        else:
            return apology("Invalid Symbol", 400)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return apology("Username/password missing", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords don't match", 400)
        elif len(db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))) != 0:
            return apology("Username taken", 400)
        else:
            db.execute("INSERT INTO 'users' ('username','hash') VALUES (:username, :hash)",
                       username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    stocks = []
    user_transactions = db.execute("SELECT * FROM transactions WHERE user_id = :id", id=session["user_id"])
    for transaction in user_transactions:
        if transaction["symbol"] not in [x[0] for x in stocks]:
            stocks.append([transaction["symbol"], 0])
        stocks[[x[0] for x in stocks].index(transaction["symbol"])][1] = stocks[
            [x[0] for x in stocks].index(transaction["symbol"])][1] + transaction["shares"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        if shares < 1:
            return apology("Invalid number of shares")
        if symbol not in [stock[0] for stock in stocks]:
            return apology("Stock not owned")
        elif shares > stocks[[x[0] for x in stocks].index(symbol)][1]:
            return apology("Not enough shares")
        else:
            price = float(lookup(request.form.get("symbol"))["price"])
            balance = db.execute("SELECT cash FROM 'users' WHERE id = :user_id", user_id=session['user_id'])[0]['cash']
            balance += price * shares
            db.execute("UPDATE users SET cash = :balance WHERE id = :user_id", user_id=session['user_id'], balance=balance)
            db.execute("INSERT INTO transactions ('user_id','symbol','price','shares','time') VALUES (:user_id, :symbol, :price, :shares, :datetime)",
                       user_id=session['user_id'], symbol=symbol, price=price, shares=-shares, datetime=str(datetime.now()))
        return redirect("/")
    else:
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
