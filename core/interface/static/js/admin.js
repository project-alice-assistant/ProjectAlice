$(function () {

	let $defaultTab = $('#adminPageTabsContainer ul li:first');
	$defaultTab.addClass('activeTab');

	function hello($icon) {
		$.ajax({
			url: '/admin/areYouHere',
			type: 'POST'
		}).done(function(response) {
			if (response['success']) {
				$icon.removeClass('fa-spin')
			} else {
				setTimeout(function () {
					hello($icon);
				}, 1000);
			}
		}).fail(function() {
			setTimeout(function () {
				hello($icon);
			}, 1000);
		});
	}

	$('.tabsContent').children().each(function () {
		if ($(this).attr('id') == $defaultTab.data('for')) {
			$(this).show();
		}
		else {
			$(this).hide();
		}
	});

	$('.tab').on('click', function () {
		let target = $(this).data('for');
		$(this).addClass('activeTab');

		$('#adminPageTabsContainer ul li').each(function () {
			if ($(this).data('for') != target) {
				$(this).removeClass('activeTab');
			}
		});

		$('.tabsContent').children().each(function () {
			if ($(this).attr('id') == target) {
				$(this).show();
			}
			else {
				$(this).hide();
			}
		});
	});

	$('#restart').on('click', function () {
		let $icon = $(this).children('.utilityIcon').children('i');
		$icon.addClass('fa-spin');
		$.ajax({
			url: '/admin/restart',
			type: 'POST'
		});
		setTimeout(function () {
			hello($icon);
		}, 5000);
	});

	$('#reboot').on('click', function () {
		let $icon = $(this).children('.utilityIcon').children('i');
		$icon.addClass('fa-spin');
		$.ajax({
			url: '/admin/reboot',
			type: 'POST'
		});
		setTimeout(function () {
			hello($icon);
		}, 10000);
	});

});
