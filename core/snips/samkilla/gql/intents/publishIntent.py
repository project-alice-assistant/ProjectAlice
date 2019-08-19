# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.intents.queries import intentsCustomDataFragment
from core.snips.samkilla.gql.intents.queries import intentsFieldsFragment
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


