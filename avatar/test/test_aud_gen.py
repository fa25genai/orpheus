import asyncio

from avatar.main import generate_audio


async def main():
    # Call the generate_audio function with defaults
    print("Testing generate_audio() ...")
    audio_path = await generate_audio(
        slide_text="Hello students! I want you to drink coffee.",
    )
    print("Result:", audio_path)


if __name__ == "__main__":
    asyncio.run(main())
