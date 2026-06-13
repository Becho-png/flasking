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

LAST_MOVIES = []
CURRENT_INDEX = 0


def normalize_title(title):
    return title.strip().lower()


def empty_movie(message):
    return {
        "title": "No Movie Found",
        "overview": message,
        "rating": 0,
        "poster": ""
    }


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

        movie = max(results, key=lambda x: x.get("vote_count", 0))

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
    global LAST_MOVIES
    global CURRENT_INDEX

    data = request.get_json() or {}

    print("KUIKA BODY:", data)

    prompt = data.get("prompt", "horror")
    mood = data.get("mood", "")

    min_imdb_raw = data.get("min_imdb")

    if min_imdb_raw is None or min_imdb_raw == "":
        min_imdb = 1
    else:
        min_imdb = float(min_imdb_raw)

    print("MIN RATING:", min_imdb)

    gpt_prompt = f"""
Recommend up to 15 REAL movies.

Genre: {prompt}
Mood: {mood}

RULES:
- Return ONLY valid JSON.
- Movies MUST match the selected genre and mood.
- Do NOT include ratings.
- Do NOT repeat the same movie.
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
            temperature=0.4
        )

        content = response.choices[0].message.content

        print("GPT RAW:", content)

        result = json.loads(content)
        movies = result.get("movies", [])

        filtered_movies = []
        seen_titles = set()

        for movie in movies:
            title = movie.get("title", "")

            if title == "":
                continue

            checked_movie = get_movie_data(title, min_imdb)

            if checked_movie is None:
                continue

            normalized = normalize_title(checked_movie.get("title", title))

            if normalized in seen_titles:
                print("SKIPPED DUPLICATE:", checked_movie.get("title"))
                continue

            seen_titles.add(normalized)
            filtered_movies.append(checked_movie)

        LAST_MOVIES = filtered_movies
        CURRENT_INDEX = 2

        first_batch = LAST_MOVIES[:2]

        while len(first_batch) < 2:
            first_batch.append(
                empty_movie("Sorry, couldn't find any other movie matching your filters.")
            )

        print("RETURN FIRST BATCH:", first_batch)

        return jsonify({
            "movies": first_batch
        })

    except Exception as e:
        print("MAIN ERROR:", str(e))

        return jsonify({
            "movies": [
                empty_movie(str(e)),
                empty_movie("Sorry, couldn't find any other movie matching your filters.")
            ]
        })


@app.route("/more", methods=["POST"])
def more_movies():
    global LAST_MOVIES
    global CURRENT_INDEX

    print("GENERATE MORE CLICKED")
    print("CURRENT INDEX:", CURRENT_INDEX)
    print("TOTAL SAVED MOVIES:", len(LAST_MOVIES))

    next_movies = LAST_MOVIES[CURRENT_INDEX:CURRENT_INDEX + 2]
    CURRENT_INDEX += 2

    while len(next_movies) < 2:
        next_movies.append(
            empty_movie("Sorry, couldn't find any other movie matching your filters.")
        )

    print("RETURN MORE MOVIES:", next_movies)

    return jsonify({
        "movies": next_movies
    })
GENRE_MAP = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "science fiction": 878,
    "sci-fi": 878,
    "thriller": 53,
    "war": 10752,
    "western": 37
}

@app.route("/now-playing", methods=["POST"])
def now_playing():
    data = request.get_json() or {}

    genre = data.get("genre", "").strip().lower()
    min_imdb_raw = data.get("min_imdb")

    if min_imdb_raw is None or min_imdb_raw == "":
        min_imdb = 1
    else:
        min_imdb = float(min_imdb_raw)

    genre_id = GENRE_MAP.get(genre)

    url = "https://api.themoviedb.org/3/movie/now_playing"
    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json"
    }

    params = {
        "language": "en-US",
        "page": 1,
        "region": "TR"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        results = data.get("results", [])
        movies = []

        for movie in results:
            rating = round(float(movie.get("vote_average", 0)), 1)
            genre_ids = movie.get("genre_ids", [])

            if genre_id is not None and genre_id not in genre_ids:
                continue

            if rating < min_imdb:
                continue

            poster_path = movie.get("poster_path")
            poster = ""
            if poster_path:
                poster = f"https://image.tmdb.org/t/p/w500{poster_path}"

            movies.append({
                "title": movie.get("title", "Unknown Movie"),
                "overview": movie.get("overview", ""),
                "rating": rating,
                "poster": poster,
                "release_date": movie.get("release_date", "")
            })

        while len(movies) < 2:
            movies.append(empty_movie("No now-playing movie found for this genre."))

        return jsonify({
            "movies": movies[:6]
        })

    except Exception as e:
        print("NOW PLAYING ERROR:", str(e))
        return jsonify({
            "movies": [
                empty_movie(str(e)),
                empty_movie("Could not fetch now-playing movies.")
            ]
        })
@app.route("/different", methods=["POST"])
def different_movies():
    data = request.get_json() or {}

    print("SHOW DIFFERENT BODY:", data)

    prompt = data.get("prompt", "horror")
    mood = data.get("mood", "")

    min_imdb_raw = data.get("min_imdb")

    if min_imdb_raw is None or min_imdb_raw == "":
        min_imdb = 1
    else:
        min_imdb = float(min_imdb_raw)

    existing_titles = data.get("existing_titles", [])

    gpt_prompt = f"""
Recommend 2 DIFFERENT REAL movies.

Genre: {prompt}
Mood: {mood}

Do NOT recommend these movies:
{existing_titles}

RULES:
- Return ONLY valid JSON.
- Movies MUST match the selected genre and mood.
- Do NOT include ratings.
- Do NOT repeat the same movie.
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
            temperature=0.9
        )

        content = response.choices[0].message.content
        print("DIFFERENT GPT RAW:", content)

        result = json.loads(content)
        movies = result.get("movies", [])

        filtered_movies = []
        seen_titles = set()

        for movie in movies:
            title = movie.get("title", "")

            if title == "":
                continue

            checked_movie = get_movie_data(title, min_imdb)

            if checked_movie is None:
                continue

            normalized = normalize_title(checked_movie.get("title", title))

            if normalized in seen_titles:
                continue

            seen_titles.add(normalized)
            filtered_movies.append(checked_movie)

        while len(filtered_movies) < 2:
            filtered_movies.append(
                empty_movie("Sorry, couldn't find a different movie matching your filters.")
            )

        print("RETURN DIFFERENT:", filtered_movies[:2])

        return jsonify({
            "movies": filtered_movies[:2]
        })

    except Exception as e:
        print("DIFFERENT ERROR:", str(e))

        return jsonify({
            "movies": [
                empty_movie(str(e)),
                empty_movie("Sorry, couldn't find a different movie matching your filters.")
            ]
        })
        
if __name__ == "__main__":
    app.run(debug=True)
