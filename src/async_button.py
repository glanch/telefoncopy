import asyncio
from gpiozero import Button
from gpiozero.pins import Factory as PinFactory


class AsyncButton:
    def __init__(self, pin, pin_factory=None):
        self.button = Button(pin, pin_factory=pin_factory)
        self._loop = asyncio.get_event_loop()
        self._event = asyncio.Event()
        self.button.when_pressed = self._handle_press
        self.button.when_deactivated = self._handle_depress

    def _handle_press(self, x):
        self._loop.call_soon_threadsafe(self._event.set)

    def _handle_depress(self, x):
        self._loop.call_soon_threadsafe(self._event.clear)

    async def wait_for_press(self):
        await self._event.wait()


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
