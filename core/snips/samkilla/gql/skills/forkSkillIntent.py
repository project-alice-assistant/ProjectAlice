# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.intents.queries import intentsCustomDataFragment
from core.snips.samkilla.gql.intents.queries import intentsFieldsFragment
from core.snips.samkilla.gql.util import gql

forkSkillIntent = gql('''
mutation forkSkillIntent(
  $skillId: ID!
  $intentId: ID!
  $newIntentName: String
) {
  forkSkillIntent(
	skillId: $skillId
	intentId: $intentId
	newIntentName: $newIntentName
  ) {
	oldIntentId
	skill {
	  id
	  version
	  intents {
		id
		version
		action
	  }
	}
	intentCopied {
	  customIntentData {
		...IntentsCustomDataFragment
	  }
	  ...IntentsFieldsFragment
	}
  }
}
${intentsFieldsFragment}
${intentsCustomDataFragment}
''', {'intentsFieldsFragment': intentsFieldsFragment, 'intentsCustomDataFragment': intentsCustomDataFragment})
