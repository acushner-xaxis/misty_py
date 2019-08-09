##### apis:
- [x] `ImageAPI(self)`
    - unable to get [save image - image file](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-image-file-)
    to work and had to go with [save image - data string](https://docs.mistyrobotics.com/misty-ii/reference/rest/#saveimage-data-string-)
    - missing validation on inputs (e.g. alpha can be set to anything)
- [x] `AudioAPI(self)`
- [x] `FaceAPI(self)`
- [x] `MovementAPI(self)`
    - `angular_vel_pct` is busted
        - misty keeps speeding up endlessly from whatever value you initially set
        - problem with the IMU not initializing
- [x] `SystemAPI(self)`
    - `help` on something like `http://192.168.86.249/api/help?command=i_am_not_real` just hangs forever
    - when not plugged in, battery charge info issues:
        - battery get call shows 0% but misty's still completely on
        - battery subscription also shows 0%
- [ ] `NavigationAPI(self)`
    - able to acquire a map, but have no idea what to do with it
    - have not attempted tracking
- [ ] `SkillAPI(self)`


##### subscriptions:

- [x] `actuator_position = 'ActuatorPosition'`
- [x] `audio_play_complete = 'AudioPlayComplete'`
- [x] `battery_charge = 'BatteryCharge'`
    - when unplugged, battery charge shows as 0%
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
 
- [x] SLAM
    - [x] streaming
    - [x] mapping
    - [x] tracking
 
##### misc:
 
 - is there an easy way to tell when face training is complete?
    - i could poll `faces.list` to see when it shows up, perhaps?
    - _check out command center_
 - is there a way to play video?
    - _put in as request_
 - easy way to center images?
    - __
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
 
 
