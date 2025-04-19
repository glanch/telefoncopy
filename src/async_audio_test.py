import asyncio
import signal


async def play_audio(file_path: str):
    """Play a WAV file using aplay. Can be cancelled/stopped."""
    process = await asyncio.create_subprocess_exec(
        "aplay", file_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    try:
        await process.wait()
    except asyncio.CancelledError:
        process.terminate()
        await process.wait()
        raise

async def play_audio_loop(file_path: str):
    """Play an audio file in a loop using ffplay. Can be cancelled/stopped."""
    process = await asyncio.create_subprocess_exec(
        "ffplay", "-nodisp", "-autoexit", "-loop", "0", file_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    try:
        await process.wait()
    except asyncio.CancelledError:
        process.terminate()
        await process.wait()
        raise




async def record_audio(output_path: str, duration: int = 10):
    """Record a WAV file using arecord for a given duration. Can be cancelled/stopped."""
    process = await asyncio.create_subprocess_exec(
        "arecord",
        "-d", str(duration),  # timeout duration in seconds
        "-f", "cd",            # CD quality (16-bit, 44100 Hz, stereo)
        "-t", "wav",
        output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )

    try:
        await asyncio.wait_for(process.wait(), timeout=duration + 1)
    except asyncio.TimeoutError:
        process.terminate()
        await process.wait()
    except asyncio.CancelledError:
        process.terminate()
        await process.wait()
        raise


# Example usage
async def main():
    try:
        print("Recording for 5 seconds...")
        await record_audio("test_output.wav", duration=5)
        print("Recording done!")

        print("Playing back...")
        await play_audio("test_output.wav")
        print("Playback done!")
    except asyncio.CancelledError:
        print("Operation cancelled!")

import asyncio

async def main():
    # Start recording for 30 seconds (but we'll cancel it early)
    print("Starting recording...")
    record_task = asyncio.create_task(record_audio("test.wav", duration=30))

    # Let it run for 2 seconds
    await asyncio.sleep(2)

    # Now cancel it
    print("Cancelling recording...")
    record_task.cancel()

    try:
        await record_task
    except asyncio.CancelledError:
        print("Recording was cancelled successfully!")

    # Start playing the file (if it was saved before cancel)
    print("Starting playback...")
    play_task = asyncio.create_task(play_audio("sounds/greeting.wav"))
    await asyncio.sleep(2)  # Play for 2 seconds
    await play_audio("sounds/goodbye.wav") # Play ping meanwhile
    print("Cancelling playback...")
    play_task.cancel()

    try:
        print("Waiting for greeting to finish...")
        await play_task
        print("Greeting finished!")
    except asyncio.CancelledError:
        print("Playback was cancelled successfully!")

if __name__ == "__main__":
    asyncio.run(main())
