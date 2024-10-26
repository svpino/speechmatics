import asyncio
import io
import os
import ssl
import sys

import pyaudio
from dotenv import load_dotenv
from speechmatics_flow.client import WebsocketClient
from speechmatics_flow.models import (
    AudioSettings,
    ConnectionSettings,
    ConversationConfig,
    Interaction,
    ServerMessageType,
)

load_dotenv()


# Create a websocket client
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
client = WebsocketClient(
    ConnectionSettings(
        url="wss://flow.api.speechmatics.com/v1/flow",
        auth_token=os.getenv("SPEECHMATICS_API_KEY"),
        ssl_context=ssl_context,
    )
)

# Create a buffer to store binary messages sent from the server
audio_buffer = io.BytesIO()


# Create callback function which adds binary messages to audio buffer
def binary_msg_handler(msg: bytes):
    if isinstance(msg, (bytes, bytearray)):
        audio_buffer.write(msg)


# Register the callback to be called when the client receives an audio message from the server
client.add_event_handler(ServerMessageType.audio, binary_msg_handler)


async def audio_playback():
    """Read from buffer and play audio back to the user"""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
    try:
        while True:
            # Get the current value from the buffer
            audio_to_play = audio_buffer.getvalue()
            # Only proceed if there is audio data to play
            if audio_to_play:
                stream.write(audio_to_play)
                audio_buffer.seek(0)
                audio_buffer.truncate(0)
            # Pause briefly before checking the buffer again
            await asyncio.sleep(0.05)
    finally:
        stream.close()
        stream.stop_stream()
        p.terminate()


async def main():
    tasks = [
        # Use the websocket to connect to Flow Service and start a conversation
        asyncio.create_task(
            client.run(
                interactions=[Interaction(sys.stdin.buffer)],
                audio_settings=AudioSettings(),
                conversation_config=ConversationConfig(),
            )
        ),
        # Run audio playback handler which streams audio from audio buffer
        asyncio.create_task(audio_playback()),
    ]

    await asyncio.gather(*tasks)


asyncio.run(main())
