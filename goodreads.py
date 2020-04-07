
# KjCyt6CenkdHwgu2qQHo3w his key
# nFyzewnTjIGn2qGdZ2dQ my key
isbn = "0812995341"

import requests
import json


res = requests.get("https://www.goodreads.com/book/review_counts.json",
                   params={"key": "KjCyt6CenkdHwgu2qQHo3w", "isbns": "9781632168146"})


average_rating = res.json()["books"][0]["average_rating"]
ratings_count = res.json()["books"][0]["ratings_count"]
print(
    f"Book #{isbn} has {ratings_count} ratings and an average rating of {average_rating}")
