$(function () {

	let $defaultTab = $('#adminPageTabsContainer ul li:first');
	$defaultTab.addClass('activeTab');

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
	})
});
