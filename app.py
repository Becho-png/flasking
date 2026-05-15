from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Movie Recommendation API is running"
    })

def get_tmdb_movie(movie_name):
    url = "https://api.themoviedb.org/3/search/movie"

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    params = {
        "query": movie_name,
        "include_adult": "false",
        "language": "en-US",
        "page": 1
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if not data.get("results"):
        return {
            "title": movie_name,
            "rating": "N/A",
            "overview": "No overview found.",
            "poster": ""
        }

    result = data["results"][0]
    poster_path = result.get("poster_path")

    poster_url = ""
    if poster_path:
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return {
        "title": result.get("title", movie_name),
        "rating": result.get("vote_average", "N/A"),
        "overview": result.get("overview", ""),
        "poster": poster_url
    }

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json() or {}

    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({
            "movies": [],
            "message": "Please enter a movie genre, mood, actor, or similar movie."
        })

    ai_response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": """
You are a strict movie recommendation assistant.

The user will give a genre, mood, actor name, or movie preference.

Rules:
- Recommend exactly 3 real movies.
- Movies must directly match the user's request.
- If the user says horror, recommend only horror movies.
- If the user says comedy, recommend only comedy movies.
- If the user says romance, recommend only romance movies.
- If the user gives an actor, recommend movies starring that actor.
- Do not recommend generic top movies unless they match the request.
- Return ONLY movie names separated by commas.
- No numbering.
- No explanations.
"""
            },
            {
                "role": "user",
                "content": f"User preference: {prompt}"
            }
        ]
    )

    movie_text = ai_response.choices[0].message.content
    movie_names = [m.strip() for m in movie_text.split(",") if m.strip()]

    movies = []

    for movie_name in movie_names[:3]:
        movie_data = get_tmdb_movie(movie_name)
        movies.append(movie_data)

    return jsonify({
        "movies": movies
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
