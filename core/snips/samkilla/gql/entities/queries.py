# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

entityFieldsFragment = gql('''
  fragment EntityFieldsFragment on IntentEntity {
    id
    name
    author
    version
    language
    examples
    useSynonyms
    matchingStrictness
    automaticallyExtensible
    userId
    langPronunciation
    dataCount
    lastUpdatedAt
  }
''')

fullCustomEntityFieldsFragment = gql('''
  fragment FullCustomEntityFieldsFragment on IntentEntity {
    ...EntityFieldsFragment
    data {
      value
      synonyms
      fromWikilists {
        destId
        propId
        label
      }
    }
  }
  ${entityFieldsFragment}
''', {'entityFieldsFragment': entityFieldsFragment})

fullCustomEntityFieldsFragmentWithoutWikiList = gql('''
  fragment FullCustomEntityFieldsFragment on IntentEntity {
    ...EntityFieldsFragment
    data {
      value
      synonyms
    }
  }
  ${entityFieldsFragment}
''', {'entityFieldsFragment': entityFieldsFragment})

customEntitiesWithUsageQuery = gql('''
  query customEntitiesWithUsageQuery($email: String!, $lang: String) {
    entities(email: $email, lang: $lang, searchUsage: true) {
      ...EntityFieldsFragment
      usedIn {
        intentId
        intentName
      }
    }
  }
  ${entityFieldsFragment}
''', {'entityFieldsFragment': entityFieldsFragment})

fullCustomEntityQuery = gql('''
  query FullCustomEntityQuery($entityId: ID!) {
    entity(entityId: $entityId) {
      ...FullCustomEntityFieldsFragment
    }
  }
  ${fullCustomEntityFieldsFragment}
''', {'fullCustomEntityFieldsFragment': fullCustomEntityFieldsFragmentWithoutWikiList})
