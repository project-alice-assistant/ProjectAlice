from core.snips.samkilla.gql.assistants.queries import assistantFieldsFragment
from core.snips.samkilla.gql.util import gql

createAssistant = gql('''
mutation CreateAssistant($input: CreateAssistantInput!) {
	createAssistant(input: $input) {
		...AssistantFieldsFragment
		skills {
		  id
		}
	}
}
${assistantFieldsFragment}
''', {'assistantFieldsFragment': assistantFieldsFragment})
