from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from pyngrok import ngrok
from dotenv import load_dotenv
import os
load_dotenv()
# NGROK TOKEN
ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))

# FLASK
app = Flask(__name__)
CORS(app)

# OPENAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# API ENDPOINT
@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.json
    prompt = data.get("prompt", "")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""
The user wants movie recommendations for this genre or mood: {prompt}.

Recommend exactly 3 movies.
Only return movie names.
Do not ask questions.
"""
            }
        ]
    )

    result = response.choices[0].message.content

    return jsonify({
        "recommendation": result
    })

# NGROK
public_url = ngrok.connect(5000)
print("NGROK URL:", public_url)

# RUN
if __name__ == "__main__":
    app.run(port=5000)