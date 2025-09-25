# movie-chatbot/backend/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
import zipfile
import io
import os
import traceback

app = Flask(__name__)
CORS(app)

# Global variable to hold the movie data
movie_ratings_df = None

def download_and_prepare_data():
    """Downloads and prepares the MovieLens dataset."""
    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    ratings_path = os.path.join(data_dir, 'u.data')
    movies_path = os.path.join(data_dir, 'u.item')

    if not (os.path.exists(ratings_path) and os.path.exists(movies_path)):
        print("Downloading MovieLens 100k dataset...")
        url = "http://files.grouplens.org/datasets/movielens/ml-100k.zip"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Raise an exception for bad status codes
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(data_dir)
            
            extracted_folder = os.path.join(data_dir, 'ml-100k')
            for filename in os.listdir(extracted_folder):
                os.rename(os.path.join(extracted_folder, filename), os.path.join(data_dir, filename))
            os.rmdir(extracted_folder)
            print("Dataset downloaded and prepared.")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading data: {e}")
            return None
        except Exception as e:
            print(f"An error occurred during data preparation: {e}")
            return None

    try:
        m_cols = ['movie_id', 'title']
        r_cols = ['user_id', 'movie_id', 'rating', 'timestamp']
        movies = pd.read_csv(movies_path, sep='|', names=m_cols, usecols=range(2), encoding='latin-1')
        ratings = pd.read_csv(ratings_path, sep='\t', names=r_cols, usecols=range(4))
        if movies.empty or ratings.empty:
            print("Movie or rating data is empty after loading.")
            return None
        return pd.merge(movies, ratings)
    except Exception as e:
        print(f"Error reading or merging data files: {e}")
        return None

def get_recommendations(movie_title, df):
    """Generates movie recommendations based on a given title."""
    try:
        movie_matrix = df.pivot_table(index='user_id', columns='title', values='rating')
        target_movie_ratings = movie_matrix[movie_title]
        
        # **THIS IS THE FIX**: The 'min_periods' argument has been removed.
        similar_movies = movie_matrix.corrwith(target_movie_ratings)
        
        corr_df = pd.DataFrame(similar_movies, columns=['Correlation'])
        corr_df.dropna(inplace=True)
        
        ratings_summary = df.groupby('title')['rating'].agg(['count', 'mean'])
        corr_df = corr_df.join(ratings_summary)
        
        # This line is still important and ensures we only recommend popular movies.
        recommendations = corr_df[corr_df['count'] > 100].sort_values('Correlation', ascending=False)
        
        return recommendations.head(6).index[1:].tolist()

    except KeyError:
        return []
    except Exception:
        print("\n--- An error occurred in get_recommendations ---")
        traceback.print_exc()
        print("--------------------------------------------------\n")
        return None

@app.route('/recommend', methods=['POST'])
def recommend():
    """API endpoint to get movie recommendations."""
    global movie_ratings_df
    if movie_ratings_df is None:
        return jsonify({"error": "Server is not ready. Movie data is still loading or failed to load."}), 503

    data = request.get_json()
    if not data or 'movie' not in data:
        return jsonify({"error": "Invalid input. Please provide a 'movie' key."}), 400

    movie_title = data['movie']
    recommendations = get_recommendations(movie_title, movie_ratings_df)

    if recommendations is None:
        return jsonify({"error": "An internal error occurred while finding recommendations."}), 500

    if not recommendations:
        response_text = f"Sorry, I couldn't find recommendations for '{movie_title}'. It might not be in the database or may not have enough ratings. Please try another one (e.g., 'Star Wars (1977)')."
        return jsonify({"response": response_text})

    rec_list_str = "\n- ".join(recommendations)
    response_text = f"Based on your interest in '{movie_title}', you might also like:\n- {rec_list_str}"
    
    return jsonify({"response": response_text})

if __name__ == '__main__':
    movie_ratings_df = download_and_prepare_data()
    if movie_ratings_df is not None:
        print("\nMovie data loaded successfully. Server is ready.")
        app.run(debug=True, port=5000)
    else:
        print("\nFailed to load movie data. Server cannot start.")