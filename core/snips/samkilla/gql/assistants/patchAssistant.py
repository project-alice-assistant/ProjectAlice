from core.snips.samkilla.gql.assistants.queries import assistantFieldsFragment
from core.snips.samkilla.gql.util import gql

patchAssistant = gql('''
mutation PatchAssistant($assistantId: ID!, $input: PatchAssistantInput!) {
  patchAssistant(id: $assistantId, input: $input) {
	...AssistantFieldsFragment
  }
}
${assistantFieldsFragment}
''', {'assistantFieldsFragment': assistantFieldsFragment})
