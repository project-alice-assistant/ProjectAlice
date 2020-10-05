$(function () {

	let locked = false;
	let relations = {};

	function areYouReady($icon) {
		$.ajax({
			url : '/admin/areYouReady/',
			type: 'POST'
		}).done(function (response) {
			if (response['success']) {
				$icon.removeClass('red');
				$icon.addClass('green');
				setTimeout(function () {
					$icon.removeClass('green');
					$icon.removeClass('fa-spin');
					locked = false;
				}, 3000);
			} else {
				setTimeout(function () {
					areYouReady($icon);
				}, 1000);
			}
		}).fail(function() {
			setTimeout(function () {
				areYouReady($icon);
			}, 1000);
		});
	}

	function handleUtilityClick($div, endpoint, timeout) {
		if (locked) {
			return;
		}

		locked = true;
		let $icon = $div.children('.utilityIcon').children('i');
		$icon.addClass('fa-spin red');
		$.ajax({
			url: '/admin/' + endpoint + '/',
			type: 'POST'
		});
		setTimeout(function () {
			areYouReady($icon);
		}, timeout);
	}

	$('#restart').on('click touchstart', function () {
		handleUtilityClick($(this), 'restart', 5000);
		return false;
	});

	$('#reboot').on('click touchstart', function () {
		handleUtilityClick($(this), 'reboot', 10000);
		return false;
	});

	$('#trainAssistant').on('click touchstart', function () {
		handleUtilityClick($(this), 'trainAssistant', 5000);
		return false;
	});

	$('#wipeAll').on('click touchstart', function () {
		handleUtilityClick($(this), 'wipeAll', 5000);
		return false;
	});

	$('#update').on('click touchstart', function () {
		handleUtilityClick($(this), 'updatee', 5000);
		return false;
	});

	$('#addUser').on('click touchstart', function () {
		handleUtilityClick($(this), 'addUser', 1000);
		return false;
	});

	$('#addWakeword').on('click touchstart', function () {
		handleUtilityClick($(this), 'addWakeword', 1000);
		return false;
	});

	$('#tuneWakeword').on('click touchstart', function () {
		handleUtilityClick($(this), 'tuneWakeword', 1000);
		return false;
	});

	$('input, select').on('change', function () {
		let newValue;

		if ($(this).is('select')) {
			newValue = $(this).children('option:selected').val();
		} else if ($(this).attr('type') == 'checkbox') {
			newValue = !!$(this).is(':checked');
		} else {
			newValue = $(this).val();
		}

		newValue = newValue.toString().toLowerCase();

		let id = $(this).attr('id');
		if (relations.hasOwnProperty(id)) {
			for (const relation of relations[id]) {
				let $container = relation.closest('.configLine');
				let condition = $container.data('condition').toLowerCase();
				let value = $container.data('value').toLowerCase();

				if ((condition == 'is' && value != newValue) || (condition == 'isnot' && value == newValue) || (condition == 'isgreater' && newValue <= value) || (condition == 'islower' && newValue >= value)) {
					relation.hide();
				} else {
					relation.show();
				}
			}
		}
	});

	// Build a parent/child relation list
	$('.configLine').each(function () {
		let parent = $(this).data('parent');
		if (parent != '') {
			if (!relations.hasOwnProperty(parent)) {
				relations[parent] = [];
			}
			relations[parent].push($(this))
		}
	});
});
