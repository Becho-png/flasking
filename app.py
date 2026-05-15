from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json
import requests

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TMDB_TOKEN = os.getenv("TMDB_TOKEN")


def get_movie_data(title, min_rating):
    try:

        url = "https://api.themoviedb.org/3/search/movie"

        headers = {
            "Authorization": f"Bearer {TMDB_TOKEN}",
            "accept": "application/json"
        }

        params = {
            "query": title
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        data = response.json()

        results = data.get("results", [])

        if len(results) == 0:
            return None

        movie = results[0]

        rating = round(float(movie.get("vote_average", 0)), 1)

        if rating < min_rating:
            return None

        poster_path = movie.get("poster_path")

        poster = ""

        if poster_path:
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}"

        return {
            "title": movie.get("title", title),
            "overview": movie.get("overview", ""),
            "rating": rating,
            "poster": poster
        }

    except Exception as e:
        print("TMDB ERROR:", str(e))
        return None


@app.route("/", methods=["GET"])
def home():
    return "Movie Recommendation API Running"


@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json() or {}

    prompt = data.get("prompt", "horror")
    mood = data.get("mood", "")

    min_imdb_raw = data.get("min_imdb")

    if min_imdb_raw is None or min_imdb_raw == "":
        min_imdb = 1
    else:
        min_imdb = float(min_imdb_raw)

    gpt_prompt = f"""
Recommend up to 10 REAL movies.

Genre: {prompt}
Mood: {mood}

RULES:
- Return ONLY valid JSON.
- Movies MUST match the selected genre and mood.
- Do NOT include ratings.
- No explanations.

JSON FORMAT:
{{
  "movies": [
    {{
      "title": "Movie Name"
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
                    "content": gpt_prompt
                }
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        result = json.loads(content)

        movies = result.get("movies", [])

        filtered_movies = []

        for movie in movies:

            title = movie.get("title", "")

            checked_movie = get_movie_data(title, min_imdb)

            if checked_movie is not None:
                filtered_movies.append(checked_movie)

            if len(filtered_movies) == 3:
                break

        if len(filtered_movies) == 0:

            return jsonify({
                "movies": [
                    {
                        "title": "No Movie Found",
                        "overview": f"No movies found with rating above {min_imdb}",
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
