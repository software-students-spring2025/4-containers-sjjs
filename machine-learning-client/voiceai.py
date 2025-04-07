import asyncio
import openai
from fpdf import FPDF
import speech_recognition as sr
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()

api_key = os.getenv("api_key")  # Replace with your key
openai.api_key = api_key


def voice_input():
    def save_transcription(text):
        with open("transcriberfile.txt", "a", encoding="utf-8") as f:
            f.write(text + "\n")

    open("transcriberfile.txt", "w").close()

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Speak (say 'end' to stop)...")
        recognizer.adjust_for_ambient_noise(source)
        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio)
                print(f"You said: {text}")
                save_transcription(text)
                if text.lower() == "end":
                    print("Terminating recording.")
                    break
            except sr.UnknownValueError:
                print("Could not understand.")
            except sr.RequestError as e:
                print(f"Speech API error: {e}")
            except KeyboardInterrupt:
                print("Stopped by user.")
                break


def read_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


async def gpt_call(text, prompt):
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
            return data['choices'][0]['message']['content']


async def run_all_prompts(file_path):
    text = read_text_file(file_path)
    context = (
        "You are an expert summarizer, please take this given text and summarize it in as much detail as possible. Please include 3-4 key sections as part of this summary. Include the summary and the summary only as part of your outputted text please. : {text}"
    )
    out = await gpt_call(text, context)
    return out

def copy_to_new_file(gpt_output):
    with open("summarized_file.txt", "w", encoding="utf-8") as file:
        file.write(gpt_output)

if __name__ == "__main__":
    print("Recording...")
    voice_input()

    print("Calling OpenAI...")
    res = asyncio.run(run_all_prompts("transcriberfile.txt"))
    print("Writing to file..")
    copy_to_new_file(res)
