# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.util import gql

editSkill = gql('''
mutation editSkill($input: PatchSkillInput!, $usePut: Boolean) {
  patchSkill(input: $input, usePut: $usePut) {
	id
	name
	imageUrl
	description
	private
	hidden
	language
	version
	canCustomize
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
}
''')
