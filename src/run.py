from statemachine import run_statemachine
from gpiozero.pins.mock import MockFactory
from async_button import AsyncButton

import asyncio

async def main():
    factory = MockFactory()
    on_hook_pin = factory.pin(17)
    off_hook_pin = factory.pin(18)
    contact_1_pin = factory.pin(27)
    contact_2_pin = factory.pin(22)

    statemachine_task = asyncio.create_task(run_statemachine(factory, on_hook_pin, off_hook_pin, contact_1_pin, contact_2_pin))
    
    async def read_user_input():
        phone_is_picked_up = False  # Initial state

        while True:
            print("\nCommands:")
            print("0: Toggle Handset (Pick up / Put down)")
            print("1: Select Contact 1")
            print("2: Select Contact 2")
            print("q: Quit")

            # Read input asynchronously
            line = await asyncio.get_event_loop().run_in_executor(None, input, ">> ")
            cmd = line.strip().lower()

            if cmd == "0":
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

            elif cmd == "1":
                print("Selecting Contact 1")
                contact_1_pin.drive_low()
                await asyncio.sleep(0.2)
                contact_1_pin.drive_high()
            elif cmd == "2":
                print("Selecting Contact 2")
                contact_2_pin.drive_low()
                await asyncio.sleep(0.2)
                contact_2_pin.drive_high()
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
    asyncio.run(main())

