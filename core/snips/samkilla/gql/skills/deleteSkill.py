# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

deleteSkill = gql('''
mutation deleteSkill($skillId: ID!) {
  deleteSkill(skillId: $skillId) {
	id
  }
}
''')
