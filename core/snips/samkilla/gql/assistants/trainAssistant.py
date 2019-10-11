from core.snips.samkilla.gql.util import gql

trainAssistant = gql('''
  mutation TrainAssistantV2($assistantId: ID!, $trainingType: String) {
    trainAssistantV2(assistantId: $assistantId, trainingType: $trainingType)
  }
''')
