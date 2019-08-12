# asyncio misty robot REST API

### WIP

- almost fully featured
- testing in progress with a field trial version
- will always remain public
- expect things to break for a bit

### installation
- use python 3.7
- should be able to install with just `pip3 install git+https://github.com/acushner-xaxis/misty_py.git`
- run `jupyter console`, import the api, and then, from there you can do things like `help(MistyAPI)`
  - additionally the nice thing is that jupyter's already in an event loop, so you can do things like `await api.movement.move_head(0, 0, 0)` directly in the console

Alternately, you can use the install shell script (if you are using Windows, you'll need [WSL](https://docs.microsoft.com/en-us/windows/wsl/about)):

Make sure Python 3.7 is installed.

```sh
curl https://raw.githubusercontent.com/acushner-xaxis/misty_py/master/install.sh | bash
```

Or check out this repository:

```sh
git clone https://github.com/acushner-xaxis/misty_py.git
cd misty_py
./install.sh
```

Then you can use the environment with:

```sh
source .virtualenv/bin/activate
```

Or just start Jupyter Notebook with:

```sh
./run-jupyter
```

### getting started

- first, export `MISTY_IP=<your_misty_ip>` in your env

##### rest calls with misty

a simple face training example:

```python
import asyncio
from misty_py.api import MistyAPI

api = MistyAPI()
await asyncio.gather(
	api.images.set_led(RGB(0, 255, 0))
	api.faces.wait_for_training('name')
)
await api.images.set_led()
```

##### websocket subscriptions with misty

subscriptions are more complicated than normal rest calls

there are a few ways to subscribe:

- via `SubType` - higher-level subscription types (e.g. `SubType.face_recognition`)
- via `LLSubType` - lower-level subscription types (e.g. `Actuator.yaw`)
- via `Sub` - combination of `SubType` and `EventCondition`s 

each time you subscribe you get a `SubId` object which can be used to interact with a given subscription


here are some examples:

```python
async def debug_handler(sp: SubPayload):
	print(sp)


# subscribe to one single higher-level subscription
# (get a self_state message every 2000 ms)
await api.ws.subscribe(SubType.self_state, debug_handler, 2000)


# subscribe to a single lower-level subscription
await api.ws.subscribe(Bump.front_right, debug_handler)


# subscribe via a higher-level `SubType` to all its lower-level `LLSubType`
# this will generate 4 separate subscriptions, one for each of `LLSubType`: `Bump`
#    - all will share the same handler
await api.ws.subscribe(SubType.bump_sensor, debug_handler, 2000)
```

##### unsubscribe

there are 3 ways to unsubscribe:

- via the `SubId` you got when you created your subscription
- via higher-level `SubType`
- via `event_name`, which will generally only need to be used in debugging


```python
await api.ws.unsubscribe(SubType.self_state)
```

##### `EventCallback`

object that combines a callback with an event.

when the callback returns a truthy value, the event will be set. useful for figuring out when something's done

```python
# example of waiting for an audio file with a certain name to complete playing

async def _handle_audio_complete(self, name):
	"""subscribe and wait for an audio complete event"""
	async def _wait_name(sp: SubPayload):
		return sp.data.message.metaData.name == name

	event = EventCallback(_wait_name)
	try:
		async with self.api.ws.sub_unsub(SubType.audio_play_complete, event):
			await event
	except asyncio.CancelledError:
		event.set()
```
