# This file makes the src directory a Python package
from gpiozero.pins.mock import MockFactory
from .statemachine import run_statemachine
from .async_button import AsyncButton

import asyncio

from . import run
def run_telephone_input_loop():
    run.main()
