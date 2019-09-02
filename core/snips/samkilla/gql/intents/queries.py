from core.snips.samkilla.gql.util import gql

intentsFieldsFragment = gql('''
fragment IntentsFieldsFragment on Intent {
    id
    name
    displayName
    slots {
      name
      id
      entityId
      missingQuestion
      required
      description
      parameters
    }
    isMine
    author
    username
    version
    language
    exampleQueries
    description
    enabledByDefault
    lastUpdatedAt
    statistics {
      qualityScore
      utterancesCount
      slotsCount
    }
  }
''')

intentsCustomDataFragment = gql('''
  fragment IntentsCustomDataFragment on CustomIntentData {
    language
    utterances {
      id
      text
      fromUtteranceImport
      isAmbiguous
      fromDataGeneration
      campaignId
      data {
        text
        range {
          start
          end
        }
        slotId
        fromAutotagging
        disableAutoSpanRange
      }
    }
  }
''')

intentsByUserIdWithUsageQuery = gql('''
query IntentsByUserIdWithUsageQuery($userId: ID!, $lang: String) {
intents(
  userId: $userId
  lang: $lang
  version: "latest"
  searchUsage: true
) {
  ...IntentsFieldsFragment
  usedIn {
	skillId
	skillName
  }
}
}
${intentsFieldsFragment}
''', {'intentsFieldsFragment': intentsFieldsFragment})

fullIntentQuery = gql('''
  query FullIntentQuery($intentId: ID!) {
    intent(intentId: $intentId, version: "latest") {
      customIntentData {
        ...IntentsCustomDataFragment
      }
      ...IntentsFieldsFragment
    }
  }
  ${intentsFieldsFragment}
  ${intentsCustomDataFragment}
''', {'intentsFieldsFragment': intentsFieldsFragment, 'intentsCustomDataFragment': intentsCustomDataFragment})
