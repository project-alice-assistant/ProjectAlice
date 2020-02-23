from dataclasses import dataclass

from core.dialog.model.DialogSession import DialogSession


@dataclass
class ASRResult:
	text: str
	session: DialogSession
	likelihood: float
	processingTime: float
