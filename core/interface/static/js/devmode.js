$(document).tooltip();

$(function () {

	let $defaultTab = $('#devmodeTabsContainer ul li:first');
	$defaultTab.addClass('activeTab');

	function toggleCreateAndUploadButtons() {
		if ($('#skillNameOk').is(':visible') && $('#skillDescOk').is(':visible')) {
			$('#createSkillButton').show();
			$('#uploadSkillButton').show();
		} else {
			$('#createSkillButton').hide();
			$('#uploadSkillButton').hide();
		}
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

	$('#skillname').on('input', function () {
		if ($(this).val().length < 8) {
			$('#skillNameOk').hide();
			$('#skillNameKo').show();
			toggleCreateAndUploadButtons();
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
			toggleCreateAndUploadButtons();
		});
	});

	$('#skilldesc').on('input', function () {
		if ($(this).val().length > 20) {
			$('#skillDescKo').hide();
			$('#skillDescOk').show();
		} else {
			$('#skillDescKo').show();
			$('#skillDescOk').hide();
		}
		toggleCreateAndUploadButtons();
	});

	$('#createSkillButton').on('click touchstart', function () {
		$.ajax({
			url: '/devmode/' + $('#skillname').val() + '/',
			type: 'PUT',
			data: {
				'description': $('#skilldesc').val(),
				'fr': ($('#fr').is(':checked')) ? 'yes' : 'no',
				'de': ($('#de').is(':checked')) ? 'yes' : 'no',
				'pipreq': $('#pipreq').val(),
				'sysreq': $('#sysreq').val(),
				'conditionOnline': ($('#conditionOnline').is(':checked')) ? 'yes' : 'no',
				'conditionASRArbitrary': ($('#conditionASRArbitrary').is(':checked')) ? 'yes' : 'no',
				'conditionSkill': $('#conditionSkill').val(),
				'conditionNotSkill': $('#conditionNotSkill').val(),
				'conditionActiveManager': $('#conditionActiveManager').val(),
				'widgets': $('#widgets').val()
			}
		}).done(function (status) {
		});
	});
});
