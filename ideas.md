##### incremental positioning
- [ ] store arm/head/etc positions and be able to increment them


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
- [ ] misty as security guard for our stuff (hat tip: josh)
- [ ] integrate with homekit?

