import os
import re
import requests
from flask import Flask, session, render_template, request, abort, jsonify
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
    result = re.sub(" +", " ", result)
    return result.strip()


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
        result = db.execute("select id from users where name = :username and password = crypt(:password, password)",
                            {"username": username, "password": password})
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
        if db.execute("select id from users where name = :username", {"username": username}).rowcount > 0:
            error["header"] = "User already exist"
            error["message"] = "Pick another name, because the one you have choosen is already taken"
            return render_template("error.html", error=error)
        else:
            db.execute("insert into users (name, password) values (:username, crypt(:password, gen_salt('bf')))",
                       {"username": username, "password": password})
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
        error["header"] = "Authenticate first!"
        error["message"] = "Please login at the wellcome page and submit valid credentials or register new user"
        return render_template("error.html", error=error)
    field = sanitize(request.form.get("field"))
    value = sanitize(request.form.get("value"))
    command = "select * from books where {} ilike '%{}%'".format(field, value)
    result = db.execute(command).fetchall()
    return render_template("search.html", result=result)


@app.route("/book/<int:bookid>")
def book(bookid):
    if session["userid"] is None or session["userid"] == 0:
        error["header"] = "Authenticate first!"
        error["message"] = "Please login at the wellcome page and submit valid credentials or register new user"
        return render_template("error.html", error=error)
    # get information about the book
    bookinfo = db.execute("select * from books where id = :bookid",
                          {"bookid": bookid}).fetchone()
    # todo: check if review already exists and hide the form
    if db.execute("select id from reviews where userid= :userid and bookid= :bookid",
                  {"userid": session["userid"], "bookid": bookid}).rowcount > 0:
        noReview = False
    else:
        noReview = True
    # get all reviews for this book
    reviews = db.execute("select rating, comments, name from reviews join users on (reviews.userid = users.id) where bookid = :bookid",
                         {"bookid": bookid}).fetchall()
    # get rating from goodreads
    isbn = bookinfo.isbn
    params = {"key": "nFyzewnTjIGn2qGdZ2dQ", "isbns": isbn}
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params=params)
    goodreads = {}
    goodreads["average_rating"] = res.json()["books"][0]["average_rating"]
    goodreads["ratings_count"] = res.json()["books"][0]["ratings_count"]
    return render_template("book.html", bookinfo=bookinfo, reviews=reviews, goodreads=goodreads, noReview=noReview)


@app.route("/review", methods=["POST"])
def review():
    if session["userid"] is None or session["userid"] == 0:
        error["header"] = "Authenticate first!"
        error["message"] = "Please login at the wellcome page and submit valid credentials or register new user"
        return render_template("error.html", error=error)
    userid = session['userid']
    bookid = request.form.get('bookid')
    reviewtext = sanitize(request.form.get('reviewtext'))
    rating = request.form.get('rating')
    if db.execute("select id from reviews where userid= :userid and bookid= :bookid",
                  {"userid": userid, "bookid": bookid}).rowcount > 0:
        error["header"] = "Error happened when submitting your review"
        error["message"] = "It appears you have already submitted review for this book"
        return render_template("error.html", error=error)
    db.execute("insert into reviews(bookid, userid, rating, comments) values (:bookid, :userid, :rating, :reviewtext)",
               {"bookid": bookid, "userid": userid, "rating": rating, "reviewtext": reviewtext})
    db.commit()
    return book(bookid)


@app.route("/api/<string:isbn>")
def api(isbn):
    isbn = sanitize(isbn)
    result = db.execute(
        "select * from books where isbn = :isbn", {"isbn": isbn})
    if result.rowcount == 0:
        abort(404)
    bookinfo = result.fetchone()
    res = {}
    res["title"] = bookinfo.title
    res["author"] = bookinfo.author
    res["year"] = bookinfo.year
    res["isbn"] = bookinfo.isbn
    result = db.execute("select count(*) as count, to_char(avg(rating),'9D9') as score from reviews where bookid = :bookid",
                        {"bookid": bookinfo.id})
    review = result.fetchone()
    if review.count > 0:
        res["review_count"] = review.count
        res["average_score"] = float(review.score)
    else:
        params = {"key": "nFyzewnTjIGn2qGdZ2dQ", "isbns": isbn}
        resp = requests.get("https://www.goodreads.com/book/review_counts.json",
                            params=params)
        res["review_count"] = resp.json()["books"][0]["ratings_count"]
        res["average_score"] = float(resp.json()["books"][0]["average_rating"])
    return jsonify(res)
