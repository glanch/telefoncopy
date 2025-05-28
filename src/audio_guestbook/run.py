from gpiozero.pins.mock import MockFactory
from gpiozero.pins.lgpio import LGPIOFactory
from .statemachine import run_statemachine
from .async_button import AsyncButton
from .audio_manager import AudioManager
from .settings import settings

import asyncio

import sys

import logging

if settings.mock_inputs:
    factory = MockFactory()
else:
    factory = LGPIOFactory()


def main():
    logging.basicConfig(level=logging.INFO)

    sys.stdout.reconfigure(line_buffering=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--check-pins":
        asyncio.run(check_pin_assignments())
    else:
        asyncio.run(run_telephone_input_loop())


async def run_telephone_input_loop():
    on_hook_pin = factory.pin(settings.pin_on,)
    off_hook_pin = factory.pin(settings.pin_off)
    number_button_pins = {num: factory.pin(
        settings.get_pin_number(str(num))) for num in range(10)}
    star_button_pin = factory.pin(settings.pin_start)
    pound_button_pin = factory.pin(settings.pin_pound)

    # Create audio manager with default devices
    audio_manager = AudioManager()

    statemachine_task = asyncio.create_task(run_statemachine(
        factory, on_hook_pin, off_hook_pin, number_button_pins, star_button_pin, pound_button_pin, audio_manager))
    if not settings.mock_inputs:
        await statemachine_task
    else:
        async def read_user_input():
            phone_is_picked_up = False  # Initial state

            while True:
                print("\nCommands:")
                print("[space]: Toggle Handset (Pick up / Put down)")
                print("*: Press Star Button")
                print("#: Press Pound Button")
                print("0-9: Press Number ")
                print("q: Quit")

                # Read input asynchronously
                line = await asyncio.get_event_loop().run_in_executor(None, input, ">> ")
                cmd = line.lower()

                if cmd == " ":
                    if not phone_is_picked_up:
                        # Pick up phone
                        on_hook_pin.drive_high()
                        off_hook_pin.drive_low()
                        print("📞 Phone picked up")
                    else:
                        # Put down phone
                        on_hook_pin.drive_low()
                        off_hook_pin.drive_high()
                        print("📴 Phone put down")
                    phone_is_picked_up = not phone_is_picked_up  # Toggle state

                elif cmd == "*":
                    print("Pressing Star Button")
                    star_button_pin.drive_low()
                    await asyncio.sleep(0.2)
                    star_button_pin.drive_high()
                elif cmd == "#":
                    print("Pressing Pound Button")
                    pound_button_pin.drive_low()
                    await asyncio.sleep(0.2)
                    pound_button_pin.drive_high()
                elif cmd.isdigit() and 0 <= int(cmd) <= 9:
                    print(f"Pressing Number {cmd}")
                    number_button_pins[int(cmd)].drive_low()
                    await asyncio.sleep(0.2)
                    number_button_pins[int(cmd)].drive_high()
                elif cmd == "q":
                    print("Exiting...")
                    return

                else:
                    print("Invalid command")
        # Create and start the input reading task
        input_task = asyncio.create_task(read_user_input())

        # Wait for either the statemachine task or input task to complete
        done, pending = await asyncio.wait(
            [statemachine_task, input_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel any remaining tasks
        for task in pending:
            task.cancel()


async def check_pin_assignments():
    on_hook_pin = factory.pin(settings.pin_on)
    off_hook_pin = factory.pin(settings.pin_off)
    number_button_pins = {num: factory.pin(
        settings.get_pin_number(str(num))) for num in range(10)}
    star_button_pin = factory.pin(settings.pin_start)
    pound_button_pin = factory.pin(settings.pin_pound)

    # Create AsyncButtons for all pins
    on_hook_button = AsyncButton(on_hook_pin.number, pin_factory=factory)
    off_hook_button = AsyncButton(off_hook_pin.number, pin_factory=factory)
    number_buttons = {num: AsyncButton(
        pin.number, pin_factory=factory) for num, pin in number_button_pins.items()}
    star_button = AsyncButton(star_button_pin.number, pin_factory=factory)
    pound_button = AsyncButton(pound_button_pin.number, pin_factory=factory)

    print("\n🔍 Pin Assignment Check")
    print("Press each button to verify it's working correctly")
    print("Press 'q' to quit\n")

    while True:
        # Create tasks for all buttons
        button_tasks = {
            "on_hook": asyncio.create_task(on_hook_button.wait_for_press()),
            "off_hook": asyncio.create_task(off_hook_button.wait_for_press()),
            "star": asyncio.create_task(star_button.wait_for_press()),
            "pound": asyncio.create_task(pound_button.wait_for_press()),
            **{f"number_{num}": asyncio.create_task(btn.wait_for_press())
               for num, btn in number_buttons.items()}
        }

        # Wait for any button press
        done, pending = await asyncio.wait(
            button_tasks.values(),
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()

        # Find which button was pressed
        for name, task in button_tasks.items():
            if task in done:
                if name.startswith("number_"):
                    num = name.split("_")[1]
                    print(
                        f"✅ Number button {num} pressed (Pin: {settings.get_pin_number(num)})")
                else:
                    pin_map = {
                        "on_hook": settings.pin_on,
                        "off_hook": settings.pin_off,
                        "star": settings.pin_start,
                        "pound": settings.pin_pound
                    }
                    print(
                        f"✅ {name.replace('_', ' ').title()} button pressed (Pin: {pin_map[name]})")
                break

if __name__ == "__main__":
    main()
