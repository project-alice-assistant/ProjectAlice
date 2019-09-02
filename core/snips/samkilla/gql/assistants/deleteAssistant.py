from core.snips.samkilla.gql.util import gql

deleteAssistant = gql('''
mutation DeleteAssistant($assistantId: ID!) {
  deleteAssistant(assistantId: $assistantId) {
	id
  }
}
''')
