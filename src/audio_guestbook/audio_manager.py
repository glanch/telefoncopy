import asyncio
from pathlib import Path
from .settings import settings

_PAPLAY = "paplay"
_FFMPEG = "ffmpeg"
_PACTL = "pactl"


class AudioManager:
    def __init__(self, 
                 pulse_sink: str | None = None,
                 pulse_source: str | None = None,
                 output_dir: str | None = None):
        """Initialize the audio manager with optional PulseAudio device configurations.
        
        Args:
            pulse_sink: PulseAudio sink name for playback (e.g. "alsa_output.pci-0000_00_1f.3.analog-stereo")
            pulse_source: PulseAudio source name for recording (e.g. "alsa_input.pci-0000_00_1f.3.analog-stereo")
            output_dir: Directory to store recorded audio files
        """
        self._pulse_sink = pulse_sink or settings.audio_sink
        self._pulse_source = pulse_source or settings.audio_source
        
    async def set_volume(self, volume_percent: int):
        """Set the volume of the audio output.
        
        Args:
            volume_percent: Volume level as a percentage (0-100)
        """
        if not self._pulse_sink:
            return

        volume_percent = max(0, min(100, volume_percent))  # Clamp between 0-100
        volume_decimal = volume_percent / 100

        cmd = [_PACTL, "set-sink-volume", self._pulse_sink, f"{volume_decimal:.2f}"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()

    async def mute(self):
        """Mute the audio output."""
        if not self._pulse_sink:
            return

        cmd = [_PACTL, "set-sink-mute", self._pulse_sink, "1"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()

    async def unmute(self):
        """Unmute the audio output."""
        if not self._pulse_sink:
            return

        cmd = [_PACTL, "set-sink-mute", self._pulse_sink, "0"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()

    async def play_audio(self, file_path: str):
        """Play an audio file using paplay. Can be cancelled/stopped."""
        cmd = [_PAPLAY]
        if self._pulse_sink:
            cmd.extend([f"--device={self._pulse_sink}"])
        cmd.append(file_path)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await process.wait()
        except asyncio.CancelledError:
            if process:
                process.terminate()
            await process.wait()
            raise

    async def play_audio_loop(self, file_path: str):
        """Play an audio file in a loop using paplay. Can be cancelled/stopped."""
        while True:
            try:
                await self.play_audio(file_path)
            except asyncio.CancelledError:
                raise

    async def record_audio(self, output_path: str, duration: int = 10):
        """Record a WAV file using ffmpeg for a given duration. Can be cancelled/stopped."""
        
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [_FFMPEG]
        if self._pulse_source:
            cmd.extend(["-f", "pulse", "-i", self._pulse_source])
        else:
            cmd.extend(["-f", "pulse", "-i", "default"])
        cmd.extend([
            "-t", str(duration),  # duration in seconds
            "-acodec", "pcm_s16le",  # 16-bit signed little-endian
            "-ar", "44100",  # 44.1 kHz
            "-ac", "2",  # stereo
            "-y",  # overwrite output file if it exists
            str(output_path)
        ])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=duration + 1)
        except asyncio.TimeoutError:
            if process:
                process.terminate()
                await process.wait()
        except asyncio.CancelledError:
            if process:
                process.terminate()
                await process.wait()
            raise 