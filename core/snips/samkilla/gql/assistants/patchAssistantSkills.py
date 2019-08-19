# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.skills.queries import skillFieldsFragment
from core.snips.samkilla.gql.util import gql

patchAssistantSkills = gql('''
mutation PatchAssistantSkills(
  $assistantId: ID!
  $input: PatchAssistantInput!
) {
  patchAssistant(id: $assistantId, input: $input) {
	id
	skills {
	  intents {
		id
		action
		version
	  }
	  ...SkillFieldsFragment
	}
  }
}
${skillFieldsFragment}
''', {'skillFieldsFragment': skillFieldsFragment})
