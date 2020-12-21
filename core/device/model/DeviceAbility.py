from enum import IntFlag


class DeviceAbility(IntFlag):
	NONE = 1 << 0
	CAPTURE_SOUND = 1 << 1
	PLAY_SOUND = 1 << 2
	DISPLAY = 1 << 4
	PHYSICAL_USER_INPUT = 1 << 8
	KEYBOARD = 1 << 16
	ALERT = 1 << 32
	NOTIFY = 1 << 64
