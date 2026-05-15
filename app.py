from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()

    genre = data.get("genre", "")
    mood = data.get("mood", "")
    min_imdb = float(data.get("min_imdb", 5.4))

    prompt = f"""
Recommend movies based on:
Genre: {genre}
Mood: {mood}

Rules:
- Return ONLY valid JSON.
- Recommend up to 3 movies.
- Every movie MUST have IMDb rating >= {min_imdb}.
- If you cannot find enough movies, return fewer movies.
- Do not invent fake IMDb ratings.
- JSON format:
{{
  "movies": [
    {{
      "title": "Movie Name",
      "year": 2020,
      "imdb": 7.5,
      "reason": "Short reason"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a movie recommendation assistant. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    content = response.choices[0].message.content

    try:
        result = json.loads(content)
    except:
        return jsonify({
            "movies": [],
            "message": "Movie recommendation could not be processed."
        })

    movies = result.get("movies", [])

    fixed_movies = []
    for movie in movies:
        try:
            imdb = float(movie.get("imdb", 0))
            if imdb >= min_imdb:
                fixed_movies.append(movie)
        except:
            continue

    if len(fixed_movies) == 0:
        return jsonify({
            "movies": [],
            "message": f"No movies found with IMDb rating {min_imdb} or higher."
        })

    return jsonify({
        "movies": fixed_movies,
        "message": "Movies found successfully."
    })


@app.route("/", methods=["GET"])
def home():
    return "Movie Recommendation API is running."


if __name__ == "__main__":
    app.run(debug=True)
