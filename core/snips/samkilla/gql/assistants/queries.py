# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

assistantFieldsFragment = gql('''
fragment AssistantFieldsFragment on Assistant {
    id
    title
    userId
    language
    confidenceThreshold
    hotwordId
    lastUpdatedAt
    platform {
      type
    }
    asr {
      type
    }
  }
''')

allAssistantsQuery = gql('''
query AssistantsQuery {
    assistants {
      ...AssistantFieldsFragment
      skills {
        id
        intents {
          id
          version
          action
        }
      }
    }
  }
  ${assistantFieldsFragment}
''', {'assistantFieldsFragment': assistantFieldsFragment})
