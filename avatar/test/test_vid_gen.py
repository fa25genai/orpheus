import asyncio
from uuid import uuid4

from avatar.main import generate_video


async def main():
    video = await generate_video(audio_path=r"/avatar/ditto-talkinghead/example/krusche_voice.wav", prompt_id=uuid4(), video_counter=1)
    print("Generated video saved at:", video)


asyncio.run(main())
