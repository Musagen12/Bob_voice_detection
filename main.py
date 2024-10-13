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

    await websocket.send_text("Ready to receive audio.")
    logging.info("Speech recognition started.")

    should_stop_recording = False  # Flag to indicate if we should stop recording

    # This function handles recognized speech
    async def recognized_handler(evt):
        nonlocal should_stop_recording
        
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text = evt.result.text
            logging.info(f"Recognized: {recognized_text}")
            
            # Send recognized text only if we are not stopping
            if not should_stop_recording:
                await websocket.send_text(recognized_text)  # Await the send_text coroutine

            if recognized_text in ["Terminate.", "Stop."]:
                should_stop_recording = True
                logging.info("Stopping recording as 'terminate' or 'stop' was recognized.")

    # Subscribe to the recognized event
    speech_recognizer.recognized.connect(lambda evt: asyncio.run(recognized_handler(evt)))

    try:
        # Start continuous recognition
        speech_recognizer.start_continuous_recognition()

        # Keep the loop running until we receive a stop command
        while not should_stop_recording:
            await asyncio.sleep(0.5)  # Small delay to keep the loop running

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected.")
    finally:
        # Stop recognition and close the websocket
        speech_recognizer.stop_continuous_recognition()
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        logging.info("Speech recognition stopped.")

if __name__ == "__main__":
    import uvicorn
    # Start the server on localhost at port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)



