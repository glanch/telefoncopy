import asyncio
from enum import Enum, auto
from pathlib import Path
import time
import random  # for simulating input
from async_audio_test import play_audio, play_audio_loop, record_audio
from async_button import AsyncButton
from gpiozero import Factory


# --- File Paths ---
FILE_PATHS = {
    'greetings': 'sounds/greeting.wav',  # 'greetings/{contact}.wav',
    'beep': 'sounds/beep.wav',
    # 'messages/{contact}_{timestamp}.wav',
    'messages': 'recordings/{contact}_{timestamp}_greeting.wav',
    'goodbye': 'sounds/goodbye.wav'  # 'goodbye.wav'
}

# --- State Machine Framework ---


class StateEnum(Enum):
    IDLE = auto()
    PICKED_UP = auto()
    SELECT_CONTACT = auto()
    PLAY_GREETING = auto()
    RECORD_MESSAGE = auto()
    GOODBYE = auto()


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


class Context:
    def __init__(self, on_hook_button: AsyncButton, off_hook_button: AsyncButton, contact_1_button: AsyncButton, contact_2_button: AsyncButton):
        self.selected_contact = None
        self.message_path = None
        self.on_hook_button = on_hook_button
        self.off_hook_button = off_hook_button
        self.contact_1_button = contact_1_button
        self.contact_2_button = contact_2_button
# --- Concrete States ---


class IdleState(State):
    async def run(self, context):
        print("🕒 Waiting for phone pickup...")
        await context.off_hook_button.wait_for_press()

        return StateEnum.PICKED_UP


class PickedUpState(HangableState):
    async def run_within(self, context):
        print("👤 Phone picked up")

        try:
            async def wait_for_contact_button(context):
                input_buttons = [context.contact_1_button,
                                context.contact_2_button]
                button_tasks = {button: asyncio.create_task(
                    button.wait_for_press()) for button in input_buttons}
                done, pending = await asyncio.wait(button_tasks.values(), return_when=asyncio.FIRST_COMPLETED)
                # Cancel the one that didn't finish
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                # done_button is the first button in button_tasks.keys() that finished in done, so we search the button in button_tasks of the first task in done
                first_done_task = next(iter(done))
                done_button = next(button for button, button_task in button_tasks.items(
                ) if button_task == first_done_task)

                return next(iter(done))  # optional: return task if needed

            loop = asyncio.create_task(play_audio_loop("sounds/waehlton.wav"))

            await wait_for_contact_button(context)
            
            loop.cancel()
            
            return StateEnum.SELECT_CONTACT

        except asyncio.CancelledError:
            loop.cancel()
            raise

class SelectContactState(HangableState):
    async def run_within(self, context):
        print("👤 Selecting contact...")
        context.selected_contact = await get_user_contact_input()
        return StateEnum.PLAY_GREETING


class PlayGreetingState(HangableState):
    async def run_within(self, context):
        print(f"📼 Playing greeting for {context.selected_contact}")
        path = FILE_PATHS['greetings'].format(contact=context.selected_contact)

        await play_audio(path)
        await play_audio(FILE_PATHS['beep'])
        
        return StateEnum.RECORD_MESSAGE

class RecordMessageState(HangableState):
    async def run_within(self, context):
        print("🎙️ Recording started...")

        filename = f"recordings/{context.selected_contact}_{int(time.time())}.wav"
        context.message_path = filename

        # Start recording task (long duration, but we might cancel it)
        await record_audio(filename)
        return StateEnum.GOODBYE
        # hangup_detected = await self.do_and_wait_for_hangup(record_task, context)
        # if hangup_detected:
        #     return StateEnum.IDLE
        # else:
        #     return StateEnum.RECORD_MESSAGE

        # hangup_detected = False
        # # Create a task to wait for hangup button press
        # hangup_task = asyncio.create_task(
        #     context.on_hook_button.wait_for_press())

        # # Wait for either recording to complete or hangup button press
        # done, pending = await asyncio.wait(
        #     [record_task, hangup_task],
        #     return_when=asyncio.FIRST_COMPLETED
        # )

        # # Cancel whichever task didn't complete
        # for task in pending:
        #     task.cancel()
        #     try:
        #         await task
        #     except asyncio.CancelledError:
        #         pass

        # # Check if hangup occurred
        # if hangup_task in done:
        #     hangup_detected = True

        # try:
        #     while not record_task.done():
        #         if await detect_on_hook():  # hook detection should return True if hangup
        #             print("☎️ Hangup detected, cancelling recording...")
        #             record_task.cancel()
        #             hangup_detected = True
        #             break
        #         await asyncio.sleep(0.2)  # Polling interval

        #     # If hangup happened, we wait briefly before saving
        #     if hangup_detected:
        #         await asyncio.sleep(0.3)

        #     await record_task  # Ensure the recording finishes (or cancellation completes)

        # except asyncio.CancelledError:
        #     print("⚠️ Recording task was cancelled externally.")

        # except Exception as e:
        #     print(f"❌ Recording error: {e}")

        # if hangup_detected:
        #     return StateEnum.IDLE
        # else:
        #     return StateEnum.GOODBYE


class GoodbyeState(HangableState):
    async def run(self, context):
        print("👋 Playing goodbye message")
        await play_audio(FILE_PATHS['goodbye'])
        return StateEnum.IDLE


# --- State Map ---

state_map = {
    StateEnum.IDLE: IdleState(),
    StateEnum.PICKED_UP: PickedUpState(),
    StateEnum.SELECT_CONTACT: SelectContactState(),
    StateEnum.PLAY_GREETING: PlayGreetingState(),
    StateEnum.RECORD_MESSAGE: RecordMessageState(),
    StateEnum.GOODBYE: GoodbyeState(),
}

# --- Async Main Loop ---


async def run_statemachine(pin_factory: Factory, on_hook_pin, off_hook_pin, contact_1_pin, contact_2_pin):
    on_hook_button = AsyncButton(on_hook_pin.number, pin_factory=pin_factory)
    off_hook_button = AsyncButton(off_hook_pin.number, pin_factory=pin_factory)
    contact_1_button = AsyncButton(
        contact_1_pin.number, pin_factory=pin_factory)
    contact_2_button = AsyncButton(
        contact_2_pin.number, pin_factory=pin_factory)
    context = Context(on_hook_button=on_hook_button, off_hook_button=off_hook_button,
                      contact_1_button=contact_1_button, contact_2_button=contact_2_button)
    state = StateEnum.IDLE

    while True:
        next_state = await state_map[state].run(context)
        state = next_state


async def get_user_contact_input():
    # Simulate contact selection
    await asyncio.sleep(0.5)
    return random.choice(['Alice']) #, 'Bob', 'Charlie'])

# --- Run It ---

if __name__ == "__main__":
    # asyncio.run(main())
    pass
