from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Movie Recommendation API is running"
    })

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")

    if not prompt:
        return jsonify({
            "recommendation": "Please enter a movie preference."
        })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a movie recommendation assistant. Always recommend movies directly. Do not ask follow-up questions."
            },
            {
                "role": "user",
                "content": f"""
The user wants movie recommendations for this genre, mood, or preference: {prompt}

Recommend exactly 3 movies.
Only return movie names.
Do not include explanations.
Do not ask questions.
"""
            }
        ]
    )

    result = response.choices[0].message.content

    return jsonify({
        "recommendation": result
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
