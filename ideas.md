##### notes/issues:
- BUG: `DisplayOnScreen` in `take_picture` does not work well - just a fuzzy blurry screen image
- BUG: recording audio is hit or miss
    - sometimes it works, sometimes it doesn't
    - keyphrase recog does NOT seem to be affected by this (i.e., her mic will still pick that up)
- BUG: if you upload audio to something like `path/audio.wav`, only `path` remains after reboot
    - example:
    - upload `path/audio.wav`
    - play `path/audio.wav`  # success
    - reboot
    - play `path/audio.wav`  # 500 error - clip not there
    - all the files are still on the device, misty just doesn't see them
- BUG: if you request, say, an audio file that doesn't exist - the call times out
    - should return immediately rather than waiting for a timeout to occur
- BUG: audio recorded on misty cannot be played on misty
  - the audio plays fine when i download it and play it locally

```text
    2019-08-14T16:23:53.5536840-07:00|INF|20192602062|5|CommandRequestHandler|REST_API IN Command: /api/audio/play SourceId: a5d74bda-0a61-4bf0-aeb9-a6c00fd2ad7f ArgumentData: {"fileName":"test6.wav","volume":100} 
    2019-08-14T16:23:53.5536840-07:00|INF|20192602062|5|CommandRequestHandler|{"api":"REST_API","direction":"IN","command":"/api/audio/play","sourceId":"a5d74bda-0a61-4bf0-aeb9-a6c00fd2ad7f","argumentData":{"fileName":"test6.wav","volume":100}} 
    2019-08-14T16:23:53.5693717-07:00|INF|20192602062|18|RemoteServiceLogger|Play file command 
    2019-08-14T16:23:53.5850171-07:00|INF|20192602062|22|RemoteServiceLogger|Playing test6.wav with volume 1.0 
    2019-08-14T16:23:53.6790877-07:00|ERR|20192602062|22|RemoteServiceLogger|Failure playing file: test6.wav 
```
- BUG: making concurrent calls to `move_head` and `display` image will result in only one of them being executed
    - misty will return 200 OK messages for both requests, but...
    - misty will either change eyes OR move head, but never both. seems like a race condition on your end
    - debug logs show nothing wrong
    - sample code that can cause the condition:

```python
    pos = 80
    for _ in range(10):
        pos *= -1
        await asyncio.gather(
            api.images.display('e_Sleeping.jpg'),
            api.movement.move_head(pos, velocity=20),
        )
        await asyncio.sleep(2)
        await api.images.display('e_DefaultContent.jpg')
```
- MINOR BUG: can upload gifs, but they don't animate
    
##### TODO:
- [ ] implement RemoveBlinkMappings - BETA
- [ ] implement SetBlinking - BETA
- [ ] implement SetBlinkSettings - BETA
- [x] implement keyword recognition
- [x] audio complete to use metadata
- [x] face training: implement awesome way
    - [x] easily chain multiple audio files together
    - [x] won't do: upload multiple images/audio files in one call
- [ ] super blinky eyes
- [x] revisit _denormalization settings
- [x] read current arm/head/etc positions
    - [ ] increment them easily
    - [ ] return to original state
- [ ] change to use real asyncio in requests (instead of `requests` library)
- [ ] implement common colors
- [ ] integrate with tensorflow face recognition - mimic emotions
- [ ] ON HOLD: change upload to include optional path
    - [ ] audio
    - [ ] images
- [x] upload a gif
    - gif doesn't animate

##### random
- [ ] read subjects of incoming emails
- [x] improved/clear face training
- [ ] theme songs associated with faces
- [ ] laser pointer ala terminator
    - [ ] enable with voice command
- [ ] ask misty where certain people are (based on calendar) and have her guide you to them
- [ ] misty spouts kaizen phrases all day
- [ ] simon - the game


##### interaction
- [ ] get a second misty and have them interact (verbal argument/roast session lol)

##### copilot
- [ ] recognize trader
- [ ] field question about strats
- [ ] hit our db
- [ ] respond with info

##### speech-to-text
- [x] use [google](https://cloud.google.com/speech-to-text/)
- [x] set up trial google account
  - $0.006 per 15 seconds, in 15 second-intervals
  - 1000 requests would be $6
- [x] test 
- [ ] end-to-end with misty

##### text-to-speech
- [x] use [google](https://cloud.google.com/text-to-speech/)
- 0 to 1 million chars free with wavenet (better voice), $16/million after that
- config:
```
        {
          "audioConfig": {
            "audioEncoding": "LINEAR16",
            "pitch": 2,
            "speakingRate": 1
          },
          "input": {
            "text": "hi, i'm co-pi-lette"
          },
          "voice": {
            "languageCode": "en-US",
            "name": "en-US-Wavenet-E"
          }
        }
```

- [x] translate to other languages (using google)

##### other
- [ ] pitch recognition
- [ ] pitch matching
- [ ] text scrolling
- [ ] video game chars
- [ ] misty as security guard for our stuff
- [ ] integrate with homekit?

##### first round of questions
 - is there an easy way to tell when face training is complete?
    - i could poll `faces.list` to see when it shows up, perhaps?
    - _check out command center_
 - is there a way to play video?
    - _put in as request_
 - easy way to center images?
    - _feature request?_
 - what about playing simple games on the display?
    - or even streaming video?
    - could be used as a way to watch stuff online
 - can we provide our own, custom key phrases?
    - _possibly in future_
 - no ability to upload multiple files concurrently
    - not that big a deal, i just noticed it didn't work
 - how do you get settings such as, e.g.:
    - current positioning for arms
    - current image displayed
 - increase file size for audio files?
    - _put in as request_
 - how do you affect mental state?
    - _probably not focused on_
 - how to set messages
    - _check command center_
