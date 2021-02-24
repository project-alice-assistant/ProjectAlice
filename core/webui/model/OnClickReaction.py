from dataclasses import dataclass, field
from typing import Any

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.webui.model.ClickReactionAction import ClickReactionAction


@dataclass
class OnClickReaction(ProjectAliceObject):

	action: ClickReactionAction
	data: Any = ''
	reply: dict = field(default_factory=dict)


	def toDict(self) -> dict:
		return {
			'action': self.action,
			'data'  : self.data,
			'reply' : self.reply
		}
