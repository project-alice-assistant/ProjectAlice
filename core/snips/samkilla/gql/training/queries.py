from core.snips.samkilla.gql.util import gql


assistantDatasetQuery = gql('''
  query AssistantDatasetQuery($assistantId: ID!, $intentId: ID!) {
    assistantIntentDataset(assistantId: $assistantId, intentId: $intentId) {
      original {
        text
        entity
        slot_name
      }
      normalized {
        text
        entity
        slot_name
      }
    }
  }
''')

trainingStatusFieldsFragment = gql('''
  fragment TrainingStatusFieldsFragment on TrainingStatus {
    inProgress
    needTraining
    trainingResult
  }
''')

