from enum import IntFlag


class DeviceAbility(IntFlag):
	NONE = 1 << 0
	IS_CORE = 1 << 1
	CAPTURE_SOUND = 1 << 2
	PLAY_SOUND = 1 << 4
	DISPLAY = 1 << 8
	PHYSICAL_USER_INPUT = 1 << 16
	KEYBOARD = 1 << 32
	ALERT = 1 << 64
	NOTIFY = 1 << 128
