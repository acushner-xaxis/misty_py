##### apis:
- [x] `ImageAPI(self)`
    - note: i was unable to get [save image - image file](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-image-file-)
    to work and had to go with [save image - data string](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-data-string-)
    `application/json`
- [x] `AudioAPI(self)`
- [ ] `FaceAPI(self)`
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
 - can we provide our own, custom key phrases?
 
 ##### TODO:
 
- [ ] implement RemoveBlinkMappings - BETA
- [ ] implement SetBlinking - BETA
- [ ] implement SetBlinkSettings - BETA
