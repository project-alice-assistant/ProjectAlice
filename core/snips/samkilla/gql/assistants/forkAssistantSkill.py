from core.snips.samkilla.gql.skills.queries import skillFieldsFragment
from core.snips.samkilla.gql.util import gql

forkAssistantSkill = gql('''
mutation forkAssistantSkill($assistantId: ID!, $skillId: ID!) {
  forkAssistantSkill(assistantId: $assistantId, skillId: $skillId) {
	copiedBundleId
	assistant {
	  id
	  title
	  userId
	  language
	  skills {
		intents {
		  id
		}
		...SkillFieldsFragment
	  }
	}
  }
}
${skillFieldsFragment}
''', {'skillFieldsFragment': skillFieldsFragment})
