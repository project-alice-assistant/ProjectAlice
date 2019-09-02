# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

skillFieldsFragment = gql('''
 fragment SkillFieldsFragment on Skill {
    id
    name
    description
    language
    userId
    username
    canCustomize
    imageUrl
    hidden
    migrated
    forked
    version
    statistics {
      qualityScore
      importCount
      copyCount
    }
    rating {
      average
      totalNumber
      myRating
    }
    comment {
      totalNumber
    }
    skillType
    actionTemplateName
    repository
    hassComponent
    parameters {
      name
      value
      defaultValue
      sensitiveValue
    }
  }
''')

skillsWithUsageQuery = gql('''
 query SkillsWithUsageQuery(
    $lang: String
    $userId: String
    $intentId: ID
    $offset: Int
    $limit: Int
    $filters: String
    $sort: String
  ) {
    skills(
      lang: $lang
      userId: $userId
      intentId: $intentId
      offset: $offset
      limit: $limit
      filters: $filters
      sort: $sort
      searchUsage: true
    ) {
      skills {
        ...SkillFieldsFragment
        intents {
          id
          action
          version
        }
        usedIn {
          assistantId
          assistantName
        }
      }
      pagination {
        offset
        limit
        total
      }
    }
  }
  ${skillFieldsFragment}
''', {'skillFieldsFragment': skillFieldsFragment})
