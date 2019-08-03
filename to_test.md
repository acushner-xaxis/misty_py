##### apis:
- [x] `ImageAPI(self)`
    - note: i was unable to get [save image - image file](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-image-file-)
    to work and had to go with [save image - data string](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-data-string-)
- [x] `AudioAPI(self)`
- [x] `FaceAPI(self)`
- [ ] `MovementAPI(self)`
- [ ] `SystemAPI(self)`
- [ ] `NavigationAPI(self)`
- [ ] `SkillAPI(self)`


##### subscriptions:

- [x] `actuator_position = 'ActuatorPosition'`
- [x] `audio_play_complete = 'AudioPlayComplete'`
- [ ] `battery_charge = 'BatteryCharge'`
- [x] `bump_sensor = 'BumpSensor'`
- [x] `drive_encoders = 'DriveEncoders'`
- [x] `face_recognition = 'FaceRecognition'`
- [x] `halt_command = 'HaltCommand'`
- [x] `imu = 'IMU'`
- [x] `locomotion_command = 'LocomotionCommand'`
- [x] `self_state = 'SelfState'`
- [ ] `serial_message = 'SerialMessage'`
- [x] `time_of_flight = 'TimeOfFlight'`
- [x] `touch_sensor = 'TouchSensor'`
- [x] `world_state = 'WorldState'`
 
- [ ] slam streaming
 
##### misc:
 
 - is there an easy way to tell when face training is complete?
    - i could poll `faces.list` to see when it shows up, perhaps?
 - is there a way to play video?
 - easy way to center images?
 - what about playing simple games on the display?
    - or even streaming video of other games?
    - could be used as a way to watch stuff online
 - can we provide our own, custom key phrases?
 - no ability to upload multiple files concurrently
    - not that big a deal, i just noticed it didn't work
 - how do you get settings such as, e.g.:
    - current positioning for arms
    - current image displayed
 - increase file size for audio files?
 
##### TODO:
 
- [ ] implement RemoveBlinkMappings - BETA
- [ ] implement SetBlinking - BETA
- [ ] implement SetBlinkSettings - BETA
