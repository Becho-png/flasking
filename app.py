from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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
            "title": str(movie_name),
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
        "title": str(result.get("title", movie_name)),
        "rating": str(result.get("vote_average", "N/A")),
        "overview": str(result.get("overview", "")),
        "poster": str(poster_url)
    }


@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.get_json() or {}

    prompt = data.get("prompt", "").strip()

    min_imdb = data.get("min_imdb", "1")

    print("USER PROMPT:", prompt)
    print("MIN IMDB:", min_imdb)

    if not prompt:

        return jsonify({
            "movies": [],
            "message": "Please enter a movie genre or mood."
        })

    ai_response = client.chat.completions.create(
        model="gpt-5.4-mini",
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": """
You are a strict movie recommendation assistant.

Rules:
- Recommend exactly 3 REAL movies.
- Movies must directly match the user's request.
- If the user says horror, recommend ONLY horror movies.
- If the user says comedy, recommend ONLY comedy movies.
- If the user says romance, recommend ONLY romance movies.
- If the user gives an actor, recommend movies starring that actor.
- Never return generic top movies unless they match the request.
- Never ask questions.
- Never explain.
- Never repeat unrelated previous answers.
- Return ONLY movie names separated by commas.
"""
            },
            {
                "role": "user",
                "content": f"""
User request: {prompt}

Minimum IMDb rating: {min_imdb}

Recommend exactly 3 movies matching this request.
Only recommend movies with IMDb rating equal to or above {min_imdb}.
Return only movie titles separated by commas.
"""
            }
        ]
    )

    movie_text = ai_response.choices[0].message.content

    print("AI RESPONSE:", movie_text)

    movie_names = [
        m.strip()
        for m in movie_text.split(",")
        if m.strip()
    ]

    movies = []

    for movie_name in movie_names[:3]:

        movie_data = get_tmdb_movie(movie_name)

        movies.append(movie_data)

    return jsonify({
        "movies": movies
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
