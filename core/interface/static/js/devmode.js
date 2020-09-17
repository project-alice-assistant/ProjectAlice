$(function () {

	let $defaultTab = $('#devmodeTabsContainer ul li:first');
	$defaultTab.addClass('activeTab');

	let $createSkillButton = $('#createSkillButton');
	let $uploadSkillButton = $('#uploadSkillButton');
	let $goGithubButton = $('#goGithubButton');

	function toggleCreateButton() {
		if ($('#skillNameOk').is(':visible') && $('#skillDescOk').is(':visible')) {
			$createSkillButton.show();
		} else {
			$createSkillButton.hide();
			$uploadSkillButton.hide();
		}
	}

	function resetSkillPage() {
		$('#newSkillForm')[0].reset();
		$('#skillNameOk').hide();
		$('#skillNameKo').show();
		$('#skillDescOk').hide();
		$('#skillDescKo').show();
		$uploadSkillButton.hide();
		$goGithubButton.hide();
	}


	$('.tabsContent').children().each(function () {
		if ($(this).attr('id') == $defaultTab.data('for')) {
			$(this).show();
		} else {
			$(this).hide();
		}
	});

	$('.tab').on('click touchstart', function () {
		let target = $(this).data('for');
		$(this).addClass('activeTab');

		$('#devmodeTabsContainer ul li').each(function () {
			if ($(this).data('for') != target) {
				$(this).removeClass('activeTab');
			}
		});

		$('.tabsContent').children().each(function () {
			if ($(this).attr('id') == target) {
				$(this).show();
			} else {
				$(this).hide();
			}
		});
		return false;
	});

	let $skillName = $('#skillName');

	$skillName.on('input', function () {
		if ($(this).val().length < 5) {
			$('#skillNameOk').hide();
			$('#skillNameKo').show();
			toggleCreateButton();
			return;
		}

		$.ajax({
			url: '/devmode/' + $(this).val() + '/',
			type: 'GET'
		}).done(function (status) {
			if (status['success']) {
				$('#skillNameOk').show();
				$('#skillNameKo').hide();
			} else {
				$('#skillNameOk').hide();
				$('#skillNameKo').show();
			}
			toggleCreateButton();
		});
	});

	$('#skillDesc').on('input', function () {
		if ($(this).val().length > 20) {
			$('#skillDescKo').hide();
			$('#skillDescOk').show();
		} else {
			$('#skillDescKo').show();
			$('#skillDescOk').hide();
		}
		toggleCreateButton();
	});

	$createSkillButton.on('click touchstart', function () {
		$.ajax({
			url: '/devmode/' + $skillName.val() + '/',
			type: 'PUT',
			data: {
				'description'           : $('#skillDesc').val(),
				'fr'                    : ($('#fr').is(':checked')) ? 'yes' : 'no',
				'de'                    : ($('#de').is(':checked')) ? 'yes' : 'no',
				'it'                    : ($('#it').is(':checked')) ? 'yes' : 'no',
				'pipreq'                : $('#pipreq').val(),
				'sysreq'                : $('#sysreq').val(),
				'conditionOnline'       : ($('#conditionOnline').is(':checked')) ? 'yes' : 'no',
				'conditionASRArbitrary' : ($('#conditionASRArbitrary').is(':checked')) ? 'yes' : 'no',
				'conditionSkill'        : $('#conditionSkill').val(),
				'conditionNotSkill'     : $('#conditionNotSkill').val(),
				'conditionActiveManager': $('#conditionActiveManager').val(),
				'widgets': $('#widgets').val()
			}
		}).done(function () {
			$('#newSkillForm :input').prop('disabled', true);
			$uploadSkillButton.prop('disabled', false).show();
			$('#resetSkillButton').prop('disabled', false);
			$createSkillButton.hide();
		});
	});

	$uploadSkillButton.on('click touchstart', function () {
		$.ajax({
			url: '/devmode/uploadToGithub/',
			type: 'POST',
			data: {
				'skillName': $('#skillName').val(),
				'skillDesc': $('#skillDesc').val()
			}
		}).done(function (status) {
			if (status['success']) {
				$uploadSkillButton.hide();
				$('#goGithubButton').text(status['url']).prop('disabled', false).show();
			}
		});
	});

	$('#resetSkillButton').on('click touchstart', function () {
		resetSkillPage();
	});

	$goGithubButton.on('click touchstart', function () {
		window.open($(this).text());
	});

	$skillName.on('keydown', function (e) {
		if (e.key == ' ') {
			return false;
		}
	});

	$('[id*=editSkill_]').on('click touchstart', function () {
		window.location.href = '/devmode/editskill/' + $(this).data('skill');
	});
});
