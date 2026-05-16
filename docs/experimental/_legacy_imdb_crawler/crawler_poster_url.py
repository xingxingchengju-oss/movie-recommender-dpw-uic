from browser_driver import BrowserDriver
from bs4 import BeautifulSoup
import time
from url_db import Database
import pandas as pd
import random


# ===============================
# Init
# ===============================
browser = BrowserDriver()

db = Database()
db.create_movie_posters_table()


# ===============================
# Read CSV
# ===============================
df = pd.read_csv("imdb_id.csv", low_memory=False)

csv_ids = df["imdb_id"].dropna().astype(str).str.strip().unique()

# keep valid imdb ids only
csv_ids = [x for x in csv_ids if x.startswith("tt")]


# ===============================
# Read Existing DB ids
# ===============================
rows = db.get_all_movie_posters()

db_ids = {row[0] for row in rows}

# only crawl missing ids
pending_ids = [x for x in csv_ids if x not in db_ids]


print("CSV IDs:", len(csv_ids))
print("Already Crawled:", len(db_ids))
print("Need Crawl:", len(pending_ids))

referer_url = "https://www.imdb.com"
browser.driver.get(referer_url)
time.sleep(10)


# ===============================
# Crawl Posters
# ===============================
for imdb_id in pending_ids:

    try:
        url = f"https://www.imdb.com/title/{imdb_id}/"

        print(f"Crawling: {imdb_id}")

        browser.get_page(url)
        print(browser.driver.current_url)

        time.sleep(random.uniform(2, 3))

        html = browser.current_page()

        soup = BeautifulSoup(html, "html.parser")

        try:
            poster = soup.find("meta", property="og:image")

            if poster:
                poster_url = poster["content"]
                db.save_movie_poster(imdb_id, poster_url)
                print("Saved:", poster_url)

            else:
                db.save_movie_poster(imdb_id, "error")
                print("Error")

        except:
            db.save_movie_poster(imdb_id, "error")
            print("Error")

    except Exception as e:
        db.save_movie_poster(imdb_id, "error")
        print("Error:", imdb_id, e)


# -------------------------------------
# Close
browser.close()
db.close()

print("Finished.")
