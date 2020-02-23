$(function () {
	function refreshData() {
		let container = $('#console');
		$.ajax({
			url: '/snipswatch/refreshConsole/',
			dataType: 'json',
			type: 'POST'
		}).done(function (response) {
			for (let i = 0; i < response.data.length; i++) {
				container.append(
					'<span class="logLine">' + response.data[i] + '</span>'
				);
			}
		}).always(function (data) {
			if ($('#checkedCheckbox').is(':visible')) {
				container.scrollTop(container.prop('scrollHeight'));
			}
		});
	}

	$('#checkedCheckbox').on('click touchstart', function () {
		$(this).hide();
		$('#emptyCheckbox').show();
		return false;
	});

	$('#emptyCheckbox').on('click touchstart', function () {
		$(this).hide();
		$('#checkedCheckbox').show();
		return false;
	});

	$('[class^="fas fa-thermometer"]').on('click touchstart', function () {
		$('[class^="fas fa-thermometer"]').removeClass('snipswatchActiveVerbosity');
		$(this).addClass('snipswatchActiveVerbosity');
		$.ajax({
			url: '/snipswatch/verbosity/',
			data: {
				verbosity: $(this).data('verbosity')
			},
			type: 'POST'
		});
		return false;
	});

	setInterval(function () {
		refreshData();
	}, 500);
});
