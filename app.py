from flask import Flask, render_template, request, jsonify, g
from models.database import get_db, init_db, close_connection
from models.recommendation import HybridRecommender
import pandas as pd
import requests
import os
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)

load_dotenv()

app = Flask(__name__)

# Initialize TMDB API
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = "https://api.themoviedb.org/3"

recommender = HybridRecommender()

# Initialize database
init_db()


@app.before_request
def before_request():
    g.db = get_db()


@app.teardown_request
def teardown_request(exception=None):
    close_connection(exception)


@app.route('/')
def home():
    # Get top rated movies from TMDB API
    response = requests.get(f"{BASE_URL}/movie/top_rated?api_key={TMDB_API_KEY}")
    top_movies = response.json().get('results', [])[2:16]

    # Get popular genres
    genres = [
        {"id": 28, "name": "Action"},
        {"id": 12, "name": "Adventure"},
        {"id": 16, "name": "Animation"},
        {"id": 35, "name": "Comedy"},
        {"id": 80, "name": "Crime"},
        {"id": 18, "name": "Drama"},
        {"id": 10751, "name": "Family"},
        {"id": 14, "name": "Fantasy"},
        {"id": 36, "name": "History"},
        {"id": 27, "name": "Horror"},
        {"id": 10402, "name": "Music"},
        {"id": 9648, "name": "Mystery"},
        {"id": 10749, "name": "Romance"},
        {"id": 878, "name": "Science Fiction"},
        {"id": 10770, "name": "TV Movie"},
        {"id": 53, "name": "Thriller"},
        {"id": 10752, "name": "War"},
        {"id": 37, "name": "Western"}
    ]

    return render_template('index.html', top_movies=top_movies, genres=genres)


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')

    if query:
        # Search TMDB API
        response = requests.get(
            f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"
        )
        results = response.json().get('results', [])
    else:
        results = []

    return render_template('search.html', results=results, query=query)


@app.route('/genre/<int:genre_id>')
def genre(genre_id):
    # Get movies by genre from TMDB API
    response = requests.get(
        f"{BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}"
    )
    movies = response.json().get('results', [])

    # List of genres with ids and names
    genres = [
        {"id": 28, "name": "Action"},
        {"id": 12, "name": "Adventure"},
        {"id": 16, "name": "Animation"},
        {"id": 35, "name": "Comedy"},
        {"id": 80, "name": "Crime"},
        {"id": 18, "name": "Drama"},
        {"id": 10751, "name": "Family"},
        {"id": 14, "name": "Fantasy"},
        {"id": 36, "name": "History"},
        {"id": 27, "name": "Horror"},
        {"id": 10402, "name": "Music"},
        {"id": 9648, "name": "Mystery"},
        {"id": 10749, "name": "Romance"},
        {"id": 878, "name": "Science Fiction"},
        {"id": 10770, "name": "TV Movie"},
        {"id": 53, "name": "Thriller"},
        {"id": 10752, "name": "War"},
        {"id": 37, "name": "Western"}
    ]

    # Find the genre name based on genre_id
    genre_name = "Unknown"
    for genre in genres:
        if genre['id'] == genre_id:
            genre_name = genre['name']
            break

    return render_template('genre.html', movies=movies, genre_name=genre_name)


def get_streaming_platforms(movie_id):
    """Get actual streaming platforms from TMDB API"""
    try:
        response = requests.get(
            f"{BASE_URL}/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
        )
        data = response.json()

        platforms = []
        if 'results' in data and 'US' in data['results']:
            us_data = data['results']['US']

            # Streaming platforms
            if 'flatrate' in us_data:
                platforms.extend([p['provider_name'] for p in us_data['flatrate']])

            # Rent options
            if 'rent' in us_data:
                platforms.extend([f"Rent on {p['provider_name']}" for p in us_data['rent']])

            # Purchase options
            if 'buy' in us_data:
                platforms.extend([f"Buy on {p['provider_name']}" for p in us_data['buy']])

        return platforms if platforms else ["Check JustWatch for availability"]

    except Exception as e:
        print(f"Error getting streaming platforms: {e}")
        return ["Availability unknown"]


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    # Get movie details
    movie_response = requests.get(f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}")
    movie = movie_response.json()

    # Get streaming platforms (real data)
    platforms = get_streaming_platforms(movie_id)

    # Get recommendations
    try:
        movies_df = pd.read_sql('SELECT * FROM movies', g.db)
        ratings_df = pd.read_sql('SELECT * FROM user_ratings', g.db)

        recommender.load_data(movies_df, ratings_df, TMDB_API_KEY)
        recommendations = recommender.hybrid_recommendations(1, movie_id, 15)

        # Ensure recommendations have overview for the template
        for rec in recommendations.to_dict('records'):
            if 'overview' not in rec or not rec['overview']:
                rec['overview'] = "No overview available"

        return render_template('recommendations.html',
                               movie=movie,
                               platforms=platforms,
                               recommendations=recommendations.to_dict('records'))

    except Exception as e:
        print(f"Recommendation error: {e}")
        # Fallback to TMDB similar movies
        response = requests.get(f"{BASE_URL}/movie/{movie_id}/similar?api_key={TMDB_API_KEY}")
        similar_movies = response.json().get('results', [])[:5]

        # Ensure similar movies have overview
        for movie in similar_movies:
            if 'overview' not in movie or not movie['overview']:
                movie['overview'] = "No overview available"

        return render_template('recommendations.html',
                               movie=movie,
                               platforms=platforms,
                               recommendations=similar_movies)


@app.route('/rate', methods=['POST'])
def rate_movie():
    data = request.json
    user_id = data.get('user_id')
    movie_id = data.get('movie_id')
    rating = data.get('rating')

    if not all([user_id, movie_id, rating]):
        return jsonify({"success": False, "error": "Missing data"})

    try:
        cursor = g.db.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_ratings (user_id, movie_id, rating) VALUES (?, ?, ?)",
            (user_id, movie_id, rating)
        )
        g.db.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)