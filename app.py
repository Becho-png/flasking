from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json
import requests

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TMDB_API_KEY = os.getenv("TMDB_API_KEY")


def get_movie_poster(title):
    try:
        url = "https://api.themoviedb.org/3/search/movie"

        params = {
            "api_key": TMDB_API_KEY,
            "query": title
        }

        response = requests.get(url, params=params)
        data = response.json()

        results = data.get("results", [])

        if len(results) > 0:
            poster_path = results[0].get("poster_path")

            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"

        return ""

    except:
        return ""


@app.route("/", methods=["GET"])
def home():
    return "Movie Recommendation API Running"


@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json() or {}

    genre = data.get("genre", "horror")
    mood = data.get("mood", "")
    min_imdb = float(data.get("min_imdb", 1))

    prompt = f"""
Recommend up to 3 REAL movies.

Genre: {genre}
Mood: {mood}
Minimum IMDb rating: {min_imdb}

RULES:
- Return ONLY valid JSON.
- Movies MUST be real.
- Movies MUST have IMDb >= {min_imdb}
- No fake ratings.
- Overview must be short.

JSON FORMAT:
{{
  "movies": [
    {{
      "title": "Movie Name",
      "overview": "Short description",
      "rating": 8.5
    }}
  ]
}}
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a movie recommendation assistant that returns only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        result = json.loads(content)

        movies = result.get("movies", [])

        filtered_movies = []

        for movie in movies:

            try:
                rating = float(movie.get("rating", 0))

                if rating >= min_imdb:

                    title = movie.get("title", "")

                    filtered_movies.append({
                        "title": title,
                        "overview": movie.get("overview", ""),
                        "rating": rating,
                        "poster": get_movie_poster(title)
                    })

            except:
                continue

        if len(filtered_movies) == 0:
            return jsonify({
                "movies": [
                    {
                        "title": "No Movie Found",
                        "overview": f"No movies found with IMDb rating above {min_imdb}",
                        "rating": 0,
                        "poster": ""
                    }
                ]
            })

        return jsonify({
            "movies": filtered_movies
        })

    except Exception as e:

        return jsonify({
            "movies": [
                {
                    "title": "Error",
                    "overview": str(e),
                    "rating": 0,
                    "poster": ""
                }
            ]
        })


if __name__ == "__main__":
    app.run(debug=True)
