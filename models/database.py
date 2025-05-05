import sqlite3
from flask import g

DATABASE = 'movies.db'

def get_db():
    """Get the database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    """Initialize the database tables"""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY,
        title TEXT,
        overview TEXT,
        genres TEXT,
        rating REAL,
        release_date TEXT,
        poster_path TEXT,
        popularity REAL,
        vote_count INTEGER
    )
    ''')

    # Create user ratings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_ratings (
        user_id INTEGER,
        movie_id INTEGER,
        rating REAL,
        PRIMARY KEY (user_id, movie_id)
    )
    ''')

    # Insert sample data with complete information
    cursor.execute("SELECT COUNT(*) FROM movies")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO movies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (278, "The Shawshank Redemption",
                 "Framed in the 1940s for the double murder of his wife and her lover, upstanding banker Andy Dufresne begins a new life at the Shawshank prison...",
                 "Drama,Crime", 8.7, "1994-09-23", "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg", 8.9, 18000),
                (238, "The Godfather",
                 "Spanning the years 1945 to 1955, a chronicle of the fictional Italian-American Corleone crime family...",
                 "Drama,Crime", 8.7, "1972-03-24", "/3bhkrj58Vtu7enYsRolD1fZdja1.jpg", 8.8, 14000),
                (157336, "Interstellar",
                 "The adventures of a group of explorers who make use of a newly discovered wormhole...",
                 "Adventure,Drama,Sci-Fi", 8.4, "2014-11-05", "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", 8.5, 22000),
                (24428, "The Avengers",
                 "Earth's mightiest heroes must come together and learn to fight as a team...",
                 "Action,Adventure,Sci-Fi", 8.0, "2012-05-04", "/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg", 8.2, 25000),
                (299536, "Avengers: Infinity War",
                 "The Avengers and their allies must be willing to sacrifice all in an attempt to defeat the powerful Thanos...",
                 "Action,Adventure,Sci-Fi", 8.4, "2018-04-27", "/7WsyChQLEftFiDOVTGkv3hFpyyt.jpg", 8.6, 23000),
                (299534, "Avengers: Endgame",
                 "After the devastating events of Avengers: Infinity War, the universe is in ruins...",
                 "Action,Adventure,Sci-Fi", 8.4, "2019-04-26", "/or06FN3Dka5tukK1e9sl16pB3iy.jpg", 8.7, 24000)
            ]
        )

    db.commit()
    db.close()

def close_connection(exception=None):
    """Close the database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()