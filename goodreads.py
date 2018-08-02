import requests
import json

isbn = "0812995341"

res = requests.get("https://www.goodreads.com/book/review_counts.json",
                   params={"key": "nFyzewnTjIGn2qGdZ2dQ", "isbns": "0812995341"})

average_rating = res.json()["books"][0]["average_rating"]
ratings_count = res.json()["books"][0]["ratings_count"]
print(
    f"Book #{isbn} has {ratings_count} ratings and an average rating of {average_rating}")
