"""Machine Learning Client for Speech-to-Text and Summarization.

Captures microphone input, transcribes it, summarizes using OpenAI,
and stores the result in a MongoDB database.
"""

import os
import asyncio
import openai
import aiohttp
from dotenv import load_dotenv
from flask import Flask, request, jsonify

app = Flask(__name__)

load_dotenv()

api_key = os.getenv("api_key")  # Make sure this is set in .env
openai.api_key = api_key


async def gpt_call(text, prompt):
    """Sends a prompt to the OpenAI API with the given text and returns the generated response."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt.format(text=text)}],
            },
        ) as response:
            data = await response.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise KeyError("Unexpected response format from OpenAI") from e


async def run_prompt(transcription):
    """Formats the transcription into a summarization prompt and returns the GPT response."""
    context = (
        "You are an expert summarizer. Take this given text and summarize it in as much detail "
        "as possible. Please include 3–4 key sections in this summary. Include the summary, and "
        "the summary only, as part of your outputted text. : {text}"
    )

    return await gpt_call(transcription, context)


@app.route("/summarize", methods=["POST"])
def summarize():
    """
    Summarize incoming transcripts
    """
    data = request.get_json()
    transcript = data.get("transcript") if data else ""
    summary = asyncio.run(run_prompt(transcript)) if data else ""
    return jsonify({"summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
