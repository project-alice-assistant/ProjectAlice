# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.skills.queries import skillFieldsFragment
from core.snips.samkilla.gql.util import gql

createSkill = gql('''
mutation createSkill($input: CreateSkillInput!) {
  createSkill(input: $input) {
	...SkillFieldsFragment
  }
},
${skillFieldsFragment}
''', {'skillFieldsFragment': skillFieldsFragment})
