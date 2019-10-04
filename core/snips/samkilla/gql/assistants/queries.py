from core.snips.samkilla.gql.util import gql
from core.snips.samkilla.gql.skills.queries import skillFieldsFragment
from core.snips.samkilla.gql.training.queries import trainingStatusFieldsFragment

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


assistantWithSkillsQuery = gql('''
  query AssistantWithSkillsQuery($assistantId: ID!) {
    assistant(assistantId: $assistantId) {
      ...AssistantFieldsFragment
      skills {
        ...SkillFieldsFragment
        intents {
          id
          version
          action
        }
      }
    }
  }
  ${assistantFieldsFragment}
  ${skillFieldsFragment}
''', {
	'assistantFieldsFragment': assistantFieldsFragment,
	'skillFieldsFragment': skillFieldsFragment
})



assistantTrainingStatusQuery = gql('''
  query AssistantTrainingStatusQuery($assistantId: ID!) {
    assistant(assistantId: $assistantId) {
      id
      training {
        nluStatus {
          ...TrainingStatusFieldsFragment
        }
        asrStatus {
          ...TrainingStatusFieldsFragment
        }
        approximateDownloadSize
      }
    }
  }
  ${trainingStatusFieldsFragment}
''',{'trainingStatusFieldsFragment': trainingStatusFieldsFragment})
