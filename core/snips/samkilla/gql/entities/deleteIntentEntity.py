# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

deleteIntentEntity = gql('''
mutation deleteIntentEntity($id: ID!, $email: String!) {
  deleteIntentEntity(id: $id, email: $email) {
	id
  }
}
''')


