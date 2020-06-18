from dataclasses import dataclass, field


@dataclass
class DialogTemplateIntent:

	name: str
	description: str
	enabledByDefault: bool
	utterances: list = field(default_factory=list)
	slots: list = field(default_factory=list)
