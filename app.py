from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os, json

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/", methods=["GET"])
def home():
    return "Movie API running"

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json() or {}

    genre = data.get("genre", "horror")
    mood = data.get("mood", "")
    min_imdb = float(data.get("min_imdb", 1))

    prompt = f"""
Recommend 3 real movies.

Genre: {genre}
Mood: {mood}
Minimum IMDb rating: {min_imdb}

IMPORTANT RULES:
- Return ONLY valid JSON.
- Every movie rating MUST be >= {min_imdb}.
- Use real well-known movies.
- Do not return movies below the minimum rating.
- If not enough movies exist, return fewer.
- Poster can be an IMDb or TMDB poster image URL. If unsure, use empty string.

JSON format:
{{
  "movies": [
    {{
      "title": "Movie title",
      "overview": "Short movie description",
      "rating": 7.5,
      "poster": ""
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
                    "content": "You recommend real movies and return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        movies = result.get("movies", [])

        filtered_movies = []
        for movie in movies:
            rating = float(movie.get("rating", 0))

            if rating >= min_imdb:
                filtered_movies.append({
                    "title": movie.get("title", ""),
                    "overview": movie.get("overview", ""),
                    "rating": rating,
                    "poster": movie.get("poster", "")
                })

        if len(filtered_movies) == 0:
            return jsonify({
                "movies": [
                    {
                        "title": "No movie found",
                        "overview": f"No {genre} movie found with IMDb rating {min_imdb} or higher.",
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
