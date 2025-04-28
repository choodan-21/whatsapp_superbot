import os
import json
from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
import requests
from dotenv import load_dotenv
from groq import Groq
from pydub import AudioSegment
import speech_recognition as sr
from gtts import gTTS
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Groq Client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Memory storage
MEMORY_FILE = "memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w') as f:
            json.dump({}, f)

    try:
        with open(MEMORY_FILE, 'r') as f:
            data = f.read()
            if not data.strip():
                return {}
            return json.loads(data)
    except (json.JSONDecodeError, ValueError):
        # If corrupted, reset memory
        with open(MEMORY_FILE, 'w') as f:
            json.dump({}, f)
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

# Chat with Groq
def chat_with_groq(message, user_id):
    memory = load_memory()
    user_memory = memory.get(user_id, [])
    
    user_memory.append({"role": "user", "content": message})

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=user_memory
    )

    bot_message = response.choices[0].message.content
    user_memory.append({"role": "assistant", "content": bot_message})

    memory[user_id] = user_memory[-20:]  # Keep last 20
    save_memory(memory)

    return bot_message

# Text to speech
def text_to_speech(text):
    tts = gTTS(text)
    filename = f"voice_{uuid.uuid4()}.mp3"
    tts.save(filename)
    return filename

# Speech to text
def speech_to_text(audio_url):
    response = requests.get(audio_url)
    filename = "audio.ogg"
    with open(filename, "wb") as f:
        f.write(response.content)

    sound = AudioSegment.from_file(filename)
    wav_filename = "audio.wav"
    sound.export(wav_filename, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_filename) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, could not understand the audio."
        except sr.RequestError:
            return "Sorry, speech service is unavailable."

# Generate image
def generate_image(prompt):
    hugging_face_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
    url = "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
    headers = {"Authorization": f"Bearer {hugging_face_api_token}"}
    payload = {"inputs": prompt}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        image_data = response.content
        filename = f"image_{uuid.uuid4()}.png"
        with open(filename, "wb") as f:
            f.write(image_data)
        return filename
    else:
        return None

# WhatsApp route
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip()
    media_url = request.values.get('MediaUrl0', '')
    sender_id = request.values.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    if media_url and "audio" in request.values.get('MediaContentType0', ''):
        # Voice message
        text = speech_to_text(media_url)
        bot_response = chat_with_groq(text, sender_id)
        voice_filename = text_to_speech(bot_response)
        msg.body(bot_response)
        msg.media(request.url_root + voice_filename)
        return str(resp)

    elif incoming_msg.lower().startswith("image:"):
        # Image generation
        prompt = incoming_msg.replace("image:", "").strip()
        image_filename = generate_image(prompt)
        if image_filename:
            msg.body(f"Here is the generated image for: {prompt}")
            msg.media(request.url_root + image_filename)
        else:
            msg.body("Sorry, failed to generate image.")
        return str(resp)

    else:
        # Normal text chat
        bot_response = chat_with_groq(incoming_msg, sender_id)
        voice_filename = text_to_speech(bot_response)
        msg.body(bot_response)
        msg.media(request.url_root + voice_filename)
        return str(resp)

# Serve files (voice, image)
@app.route("/<path:filename>", methods=["GET"])
def serve_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
