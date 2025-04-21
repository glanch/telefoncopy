import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
import time
import random  # for simulating input
from async_audio_test import play_audio, play_audio_loop, record_audio
from async_button import AsyncButton, wait_for_any_button
from contact import Contact, was_dialed
from gpiozero import Factory

BEEP_PATH = "sounds/beep.wav"
GOODBYE_PATH = "sounds/goodbye.wav"
WAEHLTON_PATH = "sounds/waehlton.wav"
UNKNOWN_NUMBER_PATH = "sounds/unknown_number.wav"
RINGBACK_PATH = "sounds/ringback_de.wav"
STAR_PATH = "sounds/tone_star.wav"
POUND_PATH = "sounds/tone_pound.wav"
NUMBER_PATHS = {
    num: f"sounds/tone_{num}.wav" for num in range(10)
}

contacts = [
    Contact(name="Alice", number=[1], greeting_path="sounds/greetings/alice.wav"),
    Contact(name="Bob", number=[2], greeting_path="sounds/greetings/bob.wav"),
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

class State:
    async def run(self, context):
        raise NotImplementedError("Each state must implement run()")


class HangableState(State):
    async def run_within(self, context):
        raise NotImplementedError(
            "Override run_within() in subclasses of HangableState")

    async def do_and_wait_for_hangup(self, do: asyncio.Task, context):
        done, pending = await asyncio.wait(
            [do, asyncio.create_task(context.on_hook_button.wait_for_press())],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return do not in done

    async def run(self, context):
        # Wrap run_within in a task
        task = asyncio.create_task(self.run_within(context))

        # Wait for task or hangup
        hangup_detected = await self.do_and_wait_for_hangup(task, context)

        if hangup_detected:
            # If hangup happened, cancel the main task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return StateEnum.IDLE
        else:
            # Main task completed, return its result
            return task.result()
# --- Context Object ---

@dataclass
class Context:
    selected_contact: Contact | None
    message_path: str | None
    on_hook_button: AsyncButton
    off_hook_button: AsyncButton
    number_buttons: dict[int, AsyncButton]
    star_button: AsyncButton
    pound_button: AsyncButton
    dialed_number: list[int] | None

    def get_buttons(self) -> list[AsyncButton]:
        return [*self.number_buttons.values(), self.star_button, self.pound_button]

# --- Concrete States ---


class IdleState(State):
    async def run(self, context):
        print("🕒 Waiting for phone pickup...")
        await context.off_hook_button.wait_for_press()

        return StateEnum.PICKED_UP


class PickedUpState(HangableState):
    async def run_within(self, context: Context):
        print("👤 Phone picked up")

        try:
            wait_for_dialing_loop = asyncio.create_task(play_audio_loop(WAEHLTON_PATH))
            
            pressed_buttons = []

            while True:
                # Only wait for timeout if already a button was pressed
                pressed_button = await wait_for_any_button(context.get_buttons(), timeout=3 if len(pressed_buttons) > 0 else None) 
                
                if not wait_for_dialing_loop.cancelled():
                    wait_for_dialing_loop.cancel()
                
                if pressed_button is None:
                    # Translate pressed_buttons to list of ints and pound and star
                    # by finding the key in the number_buttons dict and appending the number if pressed_button is in number_buttons
                    dialed_number = []
                    for pressed_button in pressed_buttons:
                        if pressed_button in context.number_buttons.values():
                            # Get number by finding key in number_buttons dict keys 
                            number = next(num for num, btn in context.number_buttons.items() if btn == pressed_button)
                            dialed_number.append(number)
                        elif pressed_button == context.star_button:
                            dialed_number.append("start")
                        elif pressed_button == context.pound_button:
                            dialed_number.append("pound")

                    context.dialed_number = dialed_number
                    print(f"🔢 Dialed number: {context.dialed_number}")
                    return StateEnum.DIALING
                else:
                    pressed_buttons.append(pressed_button)

                if pressed_button == context.star_button:
                    # Play tone_star.wav
                    await play_audio(STAR_PATH)
                elif pressed_button == context.pound_button:
                    # Play tone_pound.wav
                    await play_audio(POUND_PATH)
                elif pressed_button in context.number_buttons.values():
                    # Get number by finding key in number_buttons dict
                    number = next(num for num, btn in context.number_buttons.items() if btn == pressed_button)
                    # Play tone_<number>.wav
                    await play_audio(NUMBER_PATHS[number])

        except asyncio.CancelledError:
            wait_for_dialing_loop.cancel()
            raise

class DialingState(HangableState):
    async def run_within(self, context):
        print("👤 Dialing...")

        assert context.dialed_number is not None

        # Find out contact
        contact = await get_user_contact_input(context.dialed_number)

        # Play tones
        for number in context.dialed_number:
            if number >= 0 and number < 10:
                await play_audio(f"sounds/tone_{number}.wav")
            else:
                print(f"❌ Invalid number: {number}")
        
        # Find out contact
        contact = was_dialed(context.dialed_number, contacts)
        # If contact is None, play unknown number
        if contact is None:
            await play_audio(UNKNOWN_NUMBER_PATH)
            return StateEnum.PICKED_UP
        else:
            context.selected_contact = contact

        # Play ringback random number of times between 3 and 10
        ringback_count = random.randint(3, 10)
        print(f"🔔 Random ringback count: {ringback_count}")
        for _ in range(random.randint(3, 10)):
            await play_audio(RINGBACK_PATH)
                        
        return StateEnum.PLAY_GREETING


class SelectContactState(HangableState):
    async def run_within(self, context):
        print("👤 Selecting contact...")
        context.selected_contact = await get_user_contact_input()
        return StateEnum.PLAY_GREETING


class PlayGreetingState(HangableState):
    async def run_within(self, context):
        print(f"📼 Playing greeting for {context.selected_contact}")

        await play_audio(context.selected_contact.greeting_path)
        await play_audio(BEEP_PATH)
        
        return StateEnum.RECORD_MESSAGE

class RecordMessageState(HangableState):
    async def run_within(self, context):
        print("🎙️ Recording started...")

        # Create recordings directory if it doesn't exist
        recordings_dir = Path("recordings") / Path(context.selected_contact.name)
        recordings_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename
        filename = recordings_dir / Path(f"{int(time.time())}.wav")

        # Record audio 
        await record_audio(filename)
        return StateEnum.GOODBYE
        


class GoodbyeState(HangableState):
    async def run_within(self, context):
        print("👋 Playing goodbye message")
        await play_audio(GOODBYE_PATH)
        return StateEnum.IDLE


# --- State Map ---

state_map = {
    StateEnum.IDLE: IdleState(),
    StateEnum.PICKED_UP: PickedUpState(),
    StateEnum.SELECT_CONTACT: SelectContactState(),
    StateEnum.PLAY_GREETING: PlayGreetingState(),
    StateEnum.RECORD_MESSAGE: RecordMessageState(),
    StateEnum.GOODBYE: GoodbyeState(),
    StateEnum.DIALING: DialingState(),
}

# --- Async Main Loop ---



async def run_statemachine(pin_factory: Factory, on_hook_pin, off_hook_pin, number_button_pins: dict[int, object], star_button_pin, pound_button_pin):
    on_hook_button = AsyncButton(on_hook_pin.number, pin_factory=pin_factory)
    off_hook_button = AsyncButton(off_hook_pin.number, pin_factory=pin_factory)
    number_buttons = { num: AsyncButton(pin.number, pin_factory=pin_factory) for num, pin in number_button_pins.items() }
    star_button = AsyncButton(star_button_pin.number, pin_factory=pin_factory)
    pound_button = AsyncButton(pound_button_pin.number, pin_factory=pin_factory)

    context = Context(None, None, on_hook_button, off_hook_button, number_buttons, star_button, pound_button, None)
    state = StateEnum.IDLE

    while True:
        next_state = await state_map[state].run(context)
        state = next_state


async def get_user_contact_input(dialed_number: list[int]):
    return random.choice(['Alice']) #, 'Bob', 'Charlie'])

# --- Run It ---

if __name__ == "__main__":
    # asyncio.run(main())
    pass
