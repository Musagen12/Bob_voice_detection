from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
import os
import asyncio
import logging

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.websocket("/ws/recognize")
async def transcribe_audio(websocket: WebSocket):
    await websocket.accept()

    speech_key = os.getenv('SPEECH_KEY')
    speech_region = os.getenv('SPEECH_REGION')

    if not speech_key or not speech_region:
        await websocket.send_text("SPEECH_KEY and/or SPEECH_REGION are not set in the environment variables.")
        await websocket.close()
        return

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_recognition_language = "en-US"

    audio_input = speechsdk.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    await websocket.send_text("Listening for the trigger word...")
    logging.info("Speech recognition started.")

    should_start_recording = False  # Flag to indicate if we should start recording

    # This function handles recognized speech
    async def recognized_handler(evt):
        nonlocal should_start_recording
        
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text = evt.result.text
            logging.info(f"Recognized: {recognized_text}")
            
            if should_start_recording:
                await websocket.send_text(recognized_text)  # Send recognized text if recording is active

            # Start recording when the trigger word is detected
            if "bob" in recognized_text.lower():  # Check for the trigger word
                should_start_recording = True
                await websocket.send_text("Trigger word detected. Starting transcription...")

            # Stop recording when 'Terminate' or 'Stop' is recognized
            if recognized_text in ["Terminate.", "Stop."]:
                should_start_recording = False  # Stop recording
                await websocket.send_text("Stopping recording as 'terminate' or 'stop' was recognized.")
                # Stop the recognizer after termination
                speech_recognizer.stop_continuous_recognition()

    # Subscribe to the recognized event
    speech_recognizer.recognized.connect(lambda evt: asyncio.run(recognized_handler(evt)))

    try:
        # Start continuous recognition
        speech_recognizer.start_continuous_recognition()

        while True:
            await asyncio.sleep(0.5)  # Keep the loop running

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected.")
    finally:
        # Stop recognition and close the websocket
        speech_recognizer.stop_continuous_recognition()
        await websocket.close()  # Ensure the WebSocket is closed
        logging.info("Speech recognition stopped.")

if __name__ == "__main__":
    import uvicorn
    # Start the server on localhost at port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
