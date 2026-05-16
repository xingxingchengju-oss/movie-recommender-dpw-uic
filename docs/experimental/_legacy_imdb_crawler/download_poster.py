import pandas as pd
import requests
import os


# ===============================
# Folder
# ===============================
save_folder = "posters"
os.makedirs(save_folder, exist_ok=True)


# ===============================
# Read CSV
# ===============================
df = pd.read_csv("imdb_posters_url.csv")


# ===============================
# Download Images
# ===============================
headers = {"User-Agent": "Mozilla/5.0"}

for _, row in df.iterrows():

    imdb_id = str(row["imdb_id"]).strip()
    url = str(row["poster_url"]).strip()

    if not url or url == "error" or url == "nan":
        continue

    try:
        file_path = os.path.join(save_folder, f"{imdb_id}.jpg")

        # Skip existing
        if os.path.exists(file_path):
            print(f"Skip: {imdb_id}")
            continue

        r = requests.get(url, headers=headers, timeout=20)

        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)

            print(f"Saved: {imdb_id}.jpg")

        else:
            print(f"Failed: {imdb_id}")

    except Exception as e:
        print("Error:", imdb_id, e)

print("Finished.")
