# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.entities.queries import fullCustomEntityFieldsFragment
from core.snips.samkilla.gql.util import gql

patchIntentEntity = gql('''
mutation patchIntentEntity(
  $intentEntityId: ID!
  $input: PatchIntentEntityInput!
) {
  patchIntentEntity(id: $intentEntityId, input: $input) {
	...FullCustomEntityFieldsFragment
  }
}
${fullCustomEntityFieldsFragment}
''', {'fullCustomEntityFieldsFragment': fullCustomEntityFieldsFragment})


