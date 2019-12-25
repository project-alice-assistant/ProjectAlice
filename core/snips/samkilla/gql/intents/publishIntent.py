from core.snips.samkilla.gql.intents.queries import intentsCustomDataFragment, intentsFieldsFragment
from core.snips.samkilla.gql.util import gql

publishIntent = gql('''
mutation publishIntent($intentId: ID, $input: PublishIntentInput!) {
  publishIntent(intentId: $intentId, input: $input) {
	...IntentsFieldsFragment
	customIntentData {
	  ...IntentsCustomDataFragment
	}
  }
}
${intentsFieldsFragment}
${intentsCustomDataFragment}
''', {'intentsFieldsFragment': intentsFieldsFragment, 'intentsCustomDataFragment': intentsCustomDataFragment})

publishIntentLight = gql('''
mutation publishIntent($intentId: ID, $input: PublishIntentInput!) {
  publishIntent(intentId: $intentId, input: $input) {
	{

	}
	customIntentData {
	  ...IntentsCustomDataFragment
	}
  }
}
${intentsFieldsFragment}
${intentsCustomDataFragment}
''', {'intentsFieldsFragment': intentsFieldsFragment, 'intentsCustomDataFragment': intentsCustomDataFragment})
