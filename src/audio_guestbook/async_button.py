import asyncio
from gpiozero import Button
from gpiozero.pins import Factory as PinFactory


class AsyncButton:
    def __init__(self, pin, pin_factory=None):
        self.button = Button(pin, pin_factory=pin_factory)
        self._loop = asyncio.get_event_loop()
        self._press_event = asyncio.Event()
        self._depress_event = asyncio.Event()
        self.button.when_pressed = self._handle_press
        self.button.when_deactivated = self._handle_depress

    def _handle_press(self, x):
        self._loop.call_soon_threadsafe(self._depress_event.clear)
        self._loop.call_soon_threadsafe(self._press_event.set)

    def _handle_depress(self, x):
        self._loop.call_soon_threadsafe(self._press_event.clear)
        self._loop.call_soon_threadsafe(self._depress_event.set)
        
    async def wait_for_press_and_release(self):
        await self._press_event.wait()
        await self._depress_event.wait()
        
    async def wait_for_press(self):
        await self._press_event.wait()

    async def wait_for_depress(self):
        await self._depress_event.wait()

async def wait_for_any_button(input_buttons: list[AsyncButton], timeout: int = None) -> AsyncButton:
    button_tasks = {button: asyncio.create_task(
        button.wait_for_press_and_release()) for button in input_buttons}
    timeout_tasks = [asyncio.create_task(asyncio.sleep(timeout))] if timeout else []
    done, pending = await asyncio.wait(list(button_tasks.values()) + timeout_tasks, return_when=asyncio.FIRST_COMPLETED)
    # Cancel the others  that didn't finish
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # done_button is the first button in button_tasks.keys() that finished in done, so we search the button in button_tasks of the first task in done
    done_without_timeout = [task for task in done if task not in timeout_tasks]
    if len(done_without_timeout) > 0:
        first_done_task = next(iter(done_without_timeout))
        return next(button for button, button_task in button_tasks.items(
        ) if button_task == first_done_task)
    else:
        return None

# class AsyncButton:
#     def __init__(self, pin, pin_factory=None):
#         self.button = Button(pin, pin_factory=pin_factory)
#         self._loop = asyncio.get_event_loop()
#         self._queue = asyncio.Queue()
#         self.button.when_pressed = self._handle_press

#     def _handle_press(self):
#         self._loop.call_soon_threadsafe(self._queue.put_nowait, True)

#     async def wait_for_press(self):
#         await self._queue.get()

# class AsyncButton:
#     def __init__(self, pin, pin_factory: PinFactory = None):
#         self.button = Button(pin,pin_factory=pin_factory)
#         self._loop = asyncio.get_event_loop()
#         self._future = None
#         self.button.when_pressed = self._handle_press

#     def _handle_press(self):
#         print("Button pressed")
#         if self._future and not self._future.done():
#             self._loop.call_soon_threadsafe(self._future.set_result, True)

#     async def wait_for_press(self):
#         print("Done waiting0")
#         self._future = self._loop.create_future()
#         print("Done waiting1")
#         await self._future
#         print("Done waiting2")
#         self._future = None
#         print("Done waiting3")
from gpiozero.pins.mock import MockFactory, MockPin
import asyncio

async def test_async_button():
    # Create a mock pin and factory
    factory = MockFactory()
    mock_pin = factory.pin(17)
    
    # Pass factory into AsyncButton
    btn = AsyncButton(17, pin_factory=factory)
    # Simulate button press
    asyncio.get_event_loop().call_later(3, mock_pin.drive_low)  # simulate press after 1s
    print("Waiting for mock button press...")
    await btn.wait_for_press()
    print("Mock button was pressed!")

if __name__ == "__main__":
    asyncio.run(test_async_button())
