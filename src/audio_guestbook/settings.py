import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import find_dotenv, load_dotenv

# Load environment variables from .env file if it exists
load_dotenv(find_dotenv(usecwd=True))

def str_to_bool(value: str) -> bool:
    return value.lower() in ('true', '1', 'yes', 'on')


class Settings:
    def __init__(self):
        # Audio settings
        self.audio_sink: Optional[str] = os.getenv("AUDIO_SINK")
        self.audio_source: Optional[str] = os.getenv("AUDIO_SOURCE")
        self.output_dir: Path = Path(os.getenv("AUDIO_OUTPUT_DIR", "recordings"))
        self.mock_inputs: bool = str_to_bool(os.getenv("MOCK_INPUTS", "true"))
        self.recording_length: int = int(os.getenv("RECORDING_LENGTH", 30))
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Pin mappings
        self.pin_mappings: Dict[str, int] = {}
        
        # Load pin configurations
        for i in range(10):  # 0-9
            pin_value = os.getenv(f"PIN_{i}")
            if pin_value:
                self.pin_mappings[str(i)] = int(pin_value)
        
        # Special pins
        self.pin_on = int(os.getenv("PIN_ON", "4"))
        self.pin_off = int(os.getenv("PIN_OFF", "4"))
        self.pin_start = int(os.getenv("PIN_START", "4"))
        self.pin_pound = int(os.getenv("PIN_POUND", "4"))

    def get_pin_number(self, key: str) -> int:
        """Get the pin number for a given key (0-9, ON, OFF, START, POUND)"""
        if key.isdigit():
            return self.pin_mappings.get(key, 0)
        return getattr(self, f"pin_{key.lower()}", 0)

    def validate(self) -> bool:
        """Validate the settings configuration"""
        # Check if output directory is writable
        if not os.access(self.output_dir, os.W_OK):
            return False
            
        # Validate pin numbers are non-negative
        for pin in [self.pin_on, self.pin_off, self.pin_start, self.pin_pound] + list(self.pin_mappings.values()):
            if pin < 0:
                return False
                
        return True

# Create a global settings instance
settings = Settings() 