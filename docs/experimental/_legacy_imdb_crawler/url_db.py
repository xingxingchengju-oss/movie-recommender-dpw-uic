import sqlite3
import pandas as pd


class Database:

    def __init__(self, db_name="imdb_posters_url.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    # Create table
    def create_movie_posters_table(self):
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS imdb_posters_url (
            imdb_id TEXT UNIQUE NOT NULL,
            poster_url TEXT
        )
        """
        )
        self.conn.commit()

    # Insert / Update poster
    def save_movie_poster(self, imdb_id, poster_url):
        self.cursor.execute(
            """
        INSERT OR REPLACE INTO imdb_posters_url (imdb_id, poster_url)
        VALUES (?, ?)
        """,
            (imdb_id, poster_url),
        )
        self.conn.commit()

    # Count rows
    def count_movie_posters(self):
        self.cursor.execute(
            """
        SELECT COUNT(*)
        FROM imdb_posters_url
        """
        )
        return self.cursor.fetchone()[0]

    # Count error posters
    def count_error_posters(self):
        self.cursor.execute(
            """
        SELECT COUNT(*)
        FROM imdb_posters_url
        WHERE poster_url = ?
        """,
            ("error",),
        )
        return self.cursor.fetchone()[0]

    # Get poster by imdb_id
    def get_movie_poster(self, imdb_id):
        self.cursor.execute(
            """
        SELECT poster_url
        FROM imdb_posters_url
        WHERE imdb_id = ?
        """,
            (imdb_id,),
        )
        return self.cursor.fetchone()

    # Get all data
    def get_all_movie_posters(self):
        self.cursor.execute(
            """
        SELECT imdb_id, poster_url
        FROM imdb_posters_url
        """
        )
        return self.cursor.fetchall()

    # Delete by imdb_id
    def delete_movie_poster(self, imdb_id):
        self.cursor.execute(
            """
        DELETE FROM imdb_posters_url
        WHERE imdb_id = ?
        """,
            (imdb_id,),
        )
        self.conn.commit()

    # Delete all rows where poster_url == error
    def delete_error_posters(self):
        self.cursor.execute(
            """
            DELETE FROM imdb_posters_url
            WHERE poster_url = ?
            """,
            ("error",),
        )
        self.conn.commit()

    def export_csv(self, file_name="imdb_posters_url.csv"):
        df = pd.read_sql_query(
            """
        SELECT imdb_id, poster_url
        FROM imdb_posters_url
        """,
            self.conn,
        )

        df.to_csv(file_name, index=False, encoding="utf-8-sig")

    # Close DB
    def close(self):
        self.conn.close()
