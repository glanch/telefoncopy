from gpiozero.pins.mock import MockFactory

from audio_guestbook.audio_manager import AudioManager
from .statemachine import run_statemachine
from .async_button import AsyncButton

import asyncio

def main():
    asyncio.run(run_telephone_input_loop())

async def run_telephone_input_loop():
    factory = MockFactory()
    on_hook_pin = factory.pin(17)
    off_hook_pin = factory.pin(18)
    number_button_pins = { num: factory.pin(pin) for num, pin in enumerate(range(1, 11), start=0) }
    star_button_pin = factory.pin(23)
    pound_button_pin = factory.pin(24)
    
    audio_manager = AudioManager("alsa/plughw:4,0", "plughw:4,0")
    statemachine_task = asyncio.create_task(run_statemachine(factory, on_hook_pin, off_hook_pin, number_button_pins, star_button_pin, pound_button_pin, audio_manager))
    
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

if __name__ == "__main__":
    main()
