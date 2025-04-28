from flask import Flask, request, send_file
import os
import pyttsx3
from dotenv import load_dotenv
import speech_recognition as sr
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize pyttsx3 engine
engine = pyttsx3.init()

# Set properties for pyttsx3 (optional)
engine.setProperty('rate', 150)  # speed
engine.setProperty('volume', 1.0)  # volume

@app.route('/')
def home():
    return "WhatsApp Bot is running!"

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.form.get('Body')
    sender = request.form.get('From')
    
    if incoming_msg:
        # Here you can process the message, e.g., call a model or function
        bot_response = f"Echo: {incoming_msg}"  # Simple echo response for now

        # Text to speech
        voice_filename = text_to_speech(bot_response)
        
        if voice_filename:
            # Send the file or acknowledgment
            return send_file(voice_filename, mimetype="audio/mpeg")
        else:
            return "Failed to generate voice", 500

    return "No message received", 400

def text_to_speech(text):
    filename = "response_audio.mp3"
    try:
        engine.save_to_file(text, filename)
        engine.runAndWait()
        return filename
    except Exception as e:
        print("Text-to-speech error:", e)
        return None

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
