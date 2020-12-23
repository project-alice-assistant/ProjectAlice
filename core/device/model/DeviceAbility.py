from enum import IntFlag


class DeviceAbility(IntFlag):
	NONE = 1 << 0
	IS_CORE = 1 << 1
	IS_SATELITTE = 1 << 2
	CAPTURE_SOUND = 1 << 4
	PLAY_SOUND = 1 << 8
	DISPLAY = 1 << 16
	PHYSICAL_USER_INPUT = 1 << 32
	KEYBOARD = 1 << 64
	ALERT = 1 << 128
	NOTIFY = 1 << 256
