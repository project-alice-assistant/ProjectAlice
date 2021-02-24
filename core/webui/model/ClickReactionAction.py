from enum import Enum


class ClickReactionAction(Enum):
	NONE = 'none'
	NAVIGATE = 'navigate'
	ANSWER_STRING = 'answer_string'
	LIST_SELECT = 'list_select'
	INFO_NOTIFICATION = 'info_notification'
	SUCCESS_NOTIFICATION = 'success_notification'
	ERROR_NOTIFICATION = 'error_notification'
