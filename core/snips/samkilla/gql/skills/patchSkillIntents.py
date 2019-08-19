# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

patchSkillIntents = gql('''
mutation patchSkillIntents($input: PatchSkillInput!) {
  patchSkill(input: $input) {
	id
	version
	intents {
	  id
	  version
	  action
	}
  }
}
''')
