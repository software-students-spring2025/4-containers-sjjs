"""Machine Learning Client for Speech-to-Text and Summarization.

Captures microphone input, transcribes it, summarizes using OpenAI,
and stores the result in a MongoDB database.
"""

import os
import datetime
import openai
import speech_recognition as sr
import aiohttp
import pymongo
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify

app = Flask(__name__)

load_dotenv()
stop_recording = False

api_key = os.getenv("api_key")  # Make sure this is set in .env
openai.api_key = api_key


def voice_input():
    """Captures speech input from the microphone until 'end' + returns transcription."""
    global stop_recording
    stop_recording = False
    transcription = ""  # Initialize empty string
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Speak (say 'end' to stop)...")
        recognizer.adjust_for_ambient_noise(source)
        while True:
            if stop_recording:
                print("Recording stopped by frontend.")
                break
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio)
                print(f"You said: {text}")
                transcription += text + "\n"
            except sr.UnknownValueError:
                print("Could not understand.")
            except sr.RequestError as e:
                print(f"Speech API error: {e}")
            except KeyboardInterrupt:
                print("Stopped by user.")
                break

    return transcription


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
            return data["choices"][0]["message"]["content"]


async def run_prompt(transcription):
    """Formats the transcription into a summarization prompt and returns the GPT response."""
    context = (
        "You are an expert summarizer. Take this given text and summarize it in as much detail "
        "as possible. Please include 3–4 key sections in this summary. Include the summary, and "
        "the summary only, as part of your outputted text. : {text}"
    )

    return await gpt_call(transcription, context)


@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    transcript = data.get('transcript') if data else ''
    summary = asyncio.run(run_prompt(transcript)) if data else ''
    return jsonify({'summary': summary})


# This main block was for interactive testing:
# """
# if __name__ == "__main__":
#    print("Recording...")
#    transcription = voice_input()
#
#    print("Getting transcription...")
#    print(transcription)
#
#    print("Calling OpenAI...")
#    summary = asyncio.run(run_prompt(transcription))
#
#    print("Getting summary...")
#    print(summary)
# """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
