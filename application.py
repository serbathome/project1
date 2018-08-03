import os

import requests
from flask import Flask, session, render_template, request, abort
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

error = {}


def sanitize(input):
    temp = input.replace("'", "")
    result = temp.replace('"', '')
    return result


@app.route("/")
def index():
    if session.get("userid") is None:
        session["userid"] = 0
        return render_template("login.html", session=session)
    elif session["userid"] == 0:
        return render_template("login.html", session=session)
    else:
        return render_template("store.html", session=session)


@app.route("/store", methods=["POST", "GET"])
def store():
    if request.method == "POST":
        username = sanitize(request.form.get("username"))
        password = sanitize(request.form.get("password"))
        command = f"select id from users where name = '{username}' and password = crypt('{password}', password)"
        result = db.execute(command)
        if result.rowcount == 0:
            error["header"] = "Wrong password!"
            error["message"] = "You have entered a wrong password or maybe a wrong username. Or both."
            return render_template("error.html", error=error)
        else:
            userid = result.fetchone()[0]
            session["userid"] = userid
            return render_template("store.html", session=session)
    if request.method == "GET":
        if session["userid"] is None or session["userid"] == 0:
            error["header"] = "Authenticate first!"
            error["message"] = "Please login at the wellcome page and submit valid credentials or register new user"
            return render_template("error.html", error=error)
        else:
            return render_template("store.html", session=session)


@app.route("/newuser", methods=["POST", "GET"])
def newuser():
    if request.method == "GET":
        return render_template("newuser.html")
    if request.method == "POST":
        username = sanitize(request.form.get("username"))
        password = sanitize(request.form.get("password"))
        # check if user already exists
        if db.execute("select id from users where name = :username", {"username": username}).rowcount > 0:
            error["header"] = "User already exist"
            error["message"] = "Pick another name, because the one you have choosen is already taken"
            return render_template("error.html", error=error)
        else:
            command = f"insert into users (name, password) values ('{username}', crypt('{password}', gen_salt('bf')))"
            db.execute(command)
            db.commit()
            return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    if session["userid"] != 0:
        session["userid"] = 0
    return render_template("login.html", session=session)


@app.route("/search", methods=["POST"])
def search():
    if session["userid"] is None or session["userid"] == 0:
        return "Authenticate first"
    field = sanitize(request.form.get("field"))
    value = sanitize(request.form.get("value"))
    command = f"select * from books where {field} ilike '%{value}%'"
    result = db.execute(command).fetchall()
    return render_template("search.html", result=result)


@app.route("/book/<int:bookid>")
def book(bookid):
    if session["userid"] is None or session["userid"] == 0:
        return "Authenticate first"
    # get information about the book
    command = f"select * from books where id = {bookid}"
    bookinfo = db.execute(command).fetchone()
    # todo: check if review already exists and hide the form
    if db.execute("select id from reviews where userid= :userid and bookid= :bookid",
                  {"userid": session["userid"], "bookid": bookid}).rowcount > 0:
        noReview = False
    else:
        noReview = True
    # get all reviews for this book
    command = f"select rating, comments, name from reviews join users on (reviews.userid = users.id) where bookid = {bookid}"
    reviews = db.execute(command).fetchall()
    # get rating from goodreads
    isbn = bookinfo.isbn
    params = {"key": "nFyzewnTjIGn2qGdZ2dQ", "isbns": isbn}
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params=params)
    goodreads = {}
    goodreads["average_rating"] = res.json()["books"][0]["average_rating"]
    goodreads["ratings_count"] = res.json()["books"][0]["ratings_count"]
    result = [bookinfo, reviews, goodreads, noReview]
    return render_template("book.html", result=result)


@app.route("/review", methods=["POST"])
def review():
    if session["userid"] is None or session["userid"] == 0:
        return "Authenticate first"
    userid = session['userid']
    bookid = request.form.get('bookid')
    reviewtext = sanitize(request.form.get('reviewtext'))
    rating = request.form.get('rating')

    # todo: check if review already exists and hide the form
    if db.execute("select id from reviews where userid= :userid and bookid= :bookid",
                  {"userid": userid, "bookid": bookid}).rowcount > 0:
        error["header"] = "Error happened when submitting your review"
        error["message"] = "It appears you have already submitted review for this book"
        return render_template("error.html", error=error)

    command = f"insert into reviews(bookid, userid, rating, comments) values ({bookid}, {userid}, {rating}, '{reviewtext}')"
    db.execute(command)
    db.commit()
    # return render_template("store.html")
    return book(bookid)


@app.route("/api/<string:isbn>")
def api(isbn):
    abort(404)
