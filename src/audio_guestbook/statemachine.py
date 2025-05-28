import asyncio
from dataclasses import dataclass
import dataclasses
from enum import Enum, auto
from pathlib import Path
import time
import random  # for simulating input
from gpiozero import Factory
from .audio_manager import AudioManager
from .async_button import AsyncButton, wait_for_any_button
from .contact import Contact, was_dialed

from .settings import settings

from datetime import datetime


SOUNDS_PATH_STR = "sounds/"
SOUNDS_PATH = Path(SOUNDS_PATH_STR)
BEEP_PATH = SOUNDS_PATH / "beep.wav"
GOODBYE_PATH = SOUNDS_PATH / "goodbye.wav"
WAEHLTON_PATH = SOUNDS_PATH / "dtmf" / "dtmf-eur-dialtone.wav"
UNKNOWN_NUMBER_PATH = SOUNDS_PATH / "unknown_number.wav"
RINGBACK_PATH = SOUNDS_PATH / "dtmf" / "dtmf-eur-ringback.wav"
#STAR_PATH = SOUNDS_PATH / "tone_star.wav"
STAR_PATH = SOUNDS_PATH / "dtmf" / f"dtmf-star.wav"
POUND_PATH = SOUNDS_PATH / "dtmf" / "dtmf-pound.wav"
NUMBER_PATHS = {
    #num: SOUNDS_PATH / f"Dtmf-{num}.wav" for num in range(10)
    num: SOUNDS_PATH / "dtmf" / f"dtmf-{num}.wav" for num in range(10)
}

contacts = [
    Contact(name="JanundLydia", number=(3,0,0,5,),
            greeting_path=SOUNDS_PATH / "greetings/LydiaundJan_ampl_beep.mp3")
]

# --- State Machine Framework ---


class StateEnum(Enum):
    IDLE = auto()
    PICKED_UP = auto()
    SELECT_CONTACT = auto()
    PLAY_GREETING = auto()
    RECORD_MESSAGE = auto()
    GOODBYE = auto()
    DIALING = auto()

# --- Context Object ---
@dataclass(frozen=True)
class Context:
    dialed_number: tuple[int|str] | None
    selected_contact: Contact | None

@dataclass
class Input:
    on_hook_button: AsyncButton
    off_hook_button: AsyncButton
    number_buttons: dict[int, AsyncButton]
    star_button: AsyncButton
    pound_button: AsyncButton

    def get_buttons(self) -> list[AsyncButton]:
        return [*self.number_buttons.values(), self.star_button, self.pound_button]


class State:
    async def run(self, input: Input, context: Context, audio_manager: AudioManager) -> tuple[type['State'], Context]:
        raise NotImplementedError("Each state must implement run()")

class HangableState(State):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        raise NotImplementedError(
            "Override run_hangable() in subclasses of HangableState")

    async def do_and_wait_for_hangup(self, do: asyncio.Task, input: Input, audio_manager: AudioManager):
        done, pending = await asyncio.wait(
            [do, asyncio.create_task(input.on_hook_button.wait_for_press())],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return do not in done

    async def run(self, input: Input, context: Context, audio_manager: AudioManager):
        # Wrap run_hangable in a task
        task = asyncio.create_task(self.run_hangable(input, context, audio_manager))

        # Wait for task or hangup
        hangup_detected = await self.do_and_wait_for_hangup(task, input, audio_manager)

        if hangup_detected:
            # If hangup happened, cancel the main task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            # Return to idle state if hangup happened, no context change
            return (IdleState, Context(None, None))
        else:
            # state's run_hangable completed, return its result with state and context
            return task.result()

# --- Concrete States ---

class DisconnectState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print("👤 Call is going to be disconnected state-wise")
        
        return (PickedUpState, Context(None, None))
        
class IdleState(State):
    async def run(self, input: Input, context: Context, audio_manager: AudioManager):
        context = Context(None, None)
        print("🕒 Waiting for phone pickup...")
        await input.off_hook_button.wait_for_press()

        return (PickedUpState, context)


class PickedUpState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print("👤 Phone picked up")

        wait_for_dialing_loop = None
        try:
            await audio_manager.unmute()
            await audio_manager.set_volume(100)

            wait_for_dialing_loop = asyncio.create_task(
                audio_manager.play_audio_loop(WAEHLTON_PATH))

            pressed_buttons = []

            while True:
                # Only wait for timeout if already a button was pressed
                pressed_button = await wait_for_any_button(input.get_buttons(), timeout=3 if len(pressed_buttons) > 0 else None)

                if not wait_for_dialing_loop.cancelled():
                    wait_for_dialing_loop.cancel()

                if pressed_button is None:
                    # Translate pressed_buttons to list of ints and pound and star
                    # by finding the key in the number_buttons dict and appending the number if pressed_button is in number_buttons
                    dialed_number = []
                    for pressed_button in pressed_buttons:
                        if pressed_button in input.number_buttons.values():
                            # Get number by finding key in number_buttons dict keys
                            number = next(
                                num for num, btn in input.number_buttons.items() if btn == pressed_button)
                            dialed_number.append(number)
                        elif pressed_button == input.star_button:
                            dialed_number.append("star")
                        elif pressed_button == input.pound_button:
                            dialed_number.append("pound")

                    dialed_number = tuple(dialed_number)
                    print(f"🔢 Dialed number: {dialed_number}")
                    return (DialingState, Context(tuple(dialed_number), None))
                else:
                    pressed_buttons.append(pressed_button)

                if pressed_button == input.star_button:
                    # Play tone_star.wav
                    asyncio.create_task(audio_manager.play_audio(STAR_PATH))
                elif pressed_button == input.pound_button:
                    # Play tone_pound.wav
                    asyncio.create_task(audio_manager.play_audio(POUND_PATH))
                elif pressed_button in input.number_buttons.values():
                    # Get number by finding key in number_buttons dict
                    number = next(
                        num for num, btn in input.number_buttons.items() if btn == pressed_button)
                    # Play tone_<number>.wav
                    asyncio.create_task(audio_manager.play_audio(NUMBER_PATHS[number]))

        except asyncio.CancelledError:
            if wait_for_dialing_loop:
                wait_for_dialing_loop.cancel()
            raise


class DialingState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print("👤 Dialing...")

        assert context.dialed_number is not None

        # Play tones of dialed number
        for number in context.dialed_number:
            tone_path = None
            if (isinstance(number, int) and number >= 0 and number < 10) or (isinstance(number, str) and number in ["star", "pound"]):
                tone_path = SOUNDS_PATH / f"sounds/dtmf/dtmf-{number}-short.wav"
                await audio_manager.play_audio(tone_path)
            else:
                print(f"❌ Invalid number: {number}")
        
        # Short delay
        await asyncio.sleep(0.5)
        
        # Find out contact
        contact = was_dialed(context.dialed_number, contacts)
        # If contact is None, play unknown number sound
        if contact is None:
            await audio_manager.play_audio(UNKNOWN_NUMBER_PATH)
            return (DisconnectState, context)

        # Play ringback random number of times between 3 and 10
        ringback_count = 1# random.randint(3, 10)
        print(f"🔔 Random ringback count: {ringback_count}")
        for _ in range(0, ringback_count):
            await audio_manager.play_audio(RINGBACK_PATH)

        return (PlayGreetingState, Context(context.dialed_number, contact))


class PlayGreetingState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print(f"📼 Playing greeting for {context.selected_contact}")

        await audio_manager.play_audio(context.selected_contact.greeting_path)
        #await audio_manager.play_audio(BEEP_PATH)

        return (RecordMessageState, context)


class RecordMessageState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print("🎙️ Recording started...")

        recordings_dir = settings.output_dir

        timestamp = datetime.now()
        random_number = random.randint(0, 10**8)  # Generates a random 3-digit number

        filename = recordings_dir / Path(f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond//1000:03d}_{random_number}.wav")

        # Record audio
        await audio_manager.record_audio(filename, settings.recording_length)
        return (GoodbyeState, context)


class GoodbyeState(HangableState):
    async def run_hangable(self, input: Input, context: Context, audio_manager: AudioManager):
        print("👋 Playing goodbye message")
        await audio_manager.play_audio(GOODBYE_PATH)
        return (DisconnectState, context)


# --- State Map ---
states: dict[type[State], State] = {
    IdleState: IdleState(),
    PickedUpState: PickedUpState(),
    PlayGreetingState: PlayGreetingState(),
    RecordMessageState: RecordMessageState(),
    GoodbyeState: GoodbyeState(),
    DialingState: DialingState(),
    DisconnectState: DisconnectState(),
}

# --- Async Main Loop ---
async def run_statemachine(pin_factory: Factory, on_hook_pin, off_hook_pin, number_button_pins: dict[int, object], star_button_pin, pound_button_pin, audio_manager: AudioManager):
    on_hook_button = AsyncButton(on_hook_pin.number, pin_factory=pin_factory)
    off_hook_button = AsyncButton(off_hook_pin.number, pin_factory=pin_factory)
    number_buttons = {num: AsyncButton(
        pin.number, pin_factory=pin_factory, bounce_time=0.05) for num, pin in number_button_pins.items()}
    star_button = AsyncButton(star_button_pin.number, pin_factory=pin_factory, bounce_time=0.05)
    pound_button = AsyncButton(
        pound_button_pin.number, pin_factory=pin_factory, bounce_time=0.05)

    input = Input(on_hook_button, off_hook_button,
                      number_buttons, star_button, pound_button)
    
    context = Context(None, None)

    old_state = None
    state = IdleState

    trace: list[tuple[type[State], Context]] = [(None, dataclasses.replace(context))]
    while True:
        next_state_class, context = await states[state].run(input, context, audio_manager)
        context = dataclasses.replace(context)
        trace.append((state, context))
        old_state = state
        state = next_state_class

if __name__ == "__main__":
    # asyncio.run(main())
    pass
