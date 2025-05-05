import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import requests


class HybridRecommender:
    def __init__(self):
        self.movies_df = None
        self.ratings_df = None
        self.feature_matrix = None
        self.indices = None
        self.tmdb_api_key = None
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        self.genre_vectorizer = CountVectorizer(tokenizer=lambda x: x.split(','))

    def load_data(self, movies_df, ratings_df, tmdb_api_key=None):
        self.movies_df = movies_df.fillna('')
        self.ratings_df = ratings_df
        self.tmdb_api_key = tmdb_api_key

        # Create enhanced content features
        movies_df['content'] = (
                movies_df['overview'] + ' ' +
                movies_df['title'] + ' ' +
                movies_df['genres'].str.replace(',', ' ')
        )

        # TF-IDF Matrix
        tfidf_matrix = self.vectorizer.fit_transform(movies_df['content'])

        # Genre Matrix
        genre_matrix = self.genre_vectorizer.fit_transform(movies_df['genres'])

        # Normalize numerical features
        scaler = MinMaxScaler()
        num_features = scaler.fit_transform(movies_df[['rating', 'popularity', 'vote_count']])

        # Combine all features
        from scipy.sparse import hstack
        self.feature_matrix = hstack([tfidf_matrix, genre_matrix, num_features])

        # Create mapping from movie ID to index
        self.indices = pd.Series(movies_df.index, index=movies_df['id']).drop_duplicates()

    def get_local_recommendations(self, movie_id, num=5):
        try:
            idx = self.indices[movie_id]
            sim_scores = list(enumerate(
                cosine_similarity(self.feature_matrix[idx], self.feature_matrix)[0]
            ))

            # Sort by similarity score
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:num + 1]

            # Get movie indices and scores
            movie_indices = [i[0] for i in sim_scores]
            scores = [i[1] for i in sim_scores]

            # Get recommendations with similarity scores
            recs = self.movies_df.iloc[movie_indices][['id', 'title', 'genres', 'poster_path', 'overview']]
            recs['similarity'] = scores

            return recs[recs['similarity'] > 0.15]  # Only return good matches

        except KeyError:
            return pd.DataFrame()

    def get_tmdb_recommendations(self, movie_id, num=5):
        try:
            response = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations",
                params={"api_key": self.tmdb_api_key}
            )
            movies = response.json().get('results', [])[:num]

            return pd.DataFrame([{
                'id': m['id'],
                'title': m['title'],
                'genres': ", ".join([str(g) for g in m.get('genre_ids', [])]),
                'poster_path': m.get('poster_path', ''),
                'overview': m.get('overview', 'No overview available'),
                'similarity': m.get('vote_average', 0) / 10  # Normalized score
            } for m in movies])

        except Exception as e:
            print(f"TMDB API error: {e}")
            return pd.DataFrame()

    def hybrid_recommendations(self, user_id, movie_id, num=5):
        # Get content-based recommendations first
        local_recs = self.get_local_recommendations(movie_id, num)

        # If we need more, get from TMDB
        if len(local_recs) < num and self.tmdb_api_key:
            tmdb_recs = self.get_tmdb_recommendations(movie_id, num - len(local_recs))
            return pd.concat([local_recs, tmdb_recs]).drop_duplicates('id')

        return local_recs