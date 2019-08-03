# asyncio misty robot REST API

##### WIP

- almost fully featured
- testing in progress with a field trial version
- will always remain public

##### installation
- use python 3.7
- should be able to install with just `pip3 install git+https://github.com/acushner-xaxis/misty_py.git`
- run `jupyter console`, import the api, and then, from there you can do things like `help(MistyAPI)`
  - additionally the nice thing is that jupyter's already in an event loop, so you can do things like `await api.movement.move_head(0, 0, 0)` directly in the console
