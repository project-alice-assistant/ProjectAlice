from core.snips.samkilla.gql.entities.queries import entityFieldsFragment
from core.snips.samkilla.gql.util import gql

createIntentEntity = gql('''
mutation createIntentEntity($input: CreateIntentEntityInput!) {
  createIntentEntity(input: $input) {
	...EntityFieldsFragment
	usedIn {
	  intentId
	  intentName
	}
  }
}
${entityFieldsFragment}
''', {'entityFieldsFragment': entityFieldsFragment})
