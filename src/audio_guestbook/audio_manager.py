import asyncio
from pathlib import Path

_ARECORD = "arecord"
_MPV = "mpv"


class AudioManager:
    def __init__(self, 
                 alsa_output_device: str | None = None,
                 arecord_device: str | None = None):
        """Initialize the audio manager with optional device configurations.
        
        Args:
            alsa_output_device: ALSA output device for mpv (e.g. "alsa/hw:0,0")
            arecord_device: ALSA device for recording (e.g. "hw:0,0")
        """
        self._alsa_output_device = alsa_output_device
        self._arecord_device = arecord_device

    async def play_audio(self, file_path: str):
        """Play an audio file using mpv. Can be cancelled/stopped."""
        cmd = [_MPV, "--no-video", "--no-terminal"]
        if self._alsa_output_device:
            cmd.extend([f"--audio-device={self._alsa_output_device}"])
        cmd.append(file_path)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise

    async def play_audio_loop(self, file_path: str):
        """Play an audio file in a loop using mpv. Can be cancelled/stopped."""
        cmd = [_MPV, "--no-video", "--no-terminal", "--loop=inf"]
        if self._alsa_output_device:
            cmd.extend([f"--audio-device={self._alsa_output_device}"])
        cmd.append(file_path)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise

    async def record_audio(self, output_path: str, duration: int = 10):
        """Record a WAV file using arecord for a given duration. Can be cancelled/stopped."""
        cmd = [_ARECORD]
        if self._arecord_device:
            cmd.extend(["-D", self._arecord_device])
        cmd.extend([
            "-d", str(duration),  # timeout duration in seconds
            "-f", "cd",          # CD quality (16-bit, 44100 Hz, stereo)
            "-t", "wav",
            output_path
        ])

        process = await asyncio.create_subprocess_exec(
            *cmd,
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