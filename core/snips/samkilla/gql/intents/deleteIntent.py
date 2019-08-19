# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

deleteIntent = gql('''
mutation deleteIntent($intentId: ID!) {
  deleteIntent(intentId: $intentId) {
	id
  }
}''')
