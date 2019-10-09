$(function () {
	function refreshData() {
		let container = $('#console');
		$.ajax({
			url: '/snipswatch/refreshConsole',
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

	$('#checkedCheckbox').on('click', function () {
		$(this).hide();
		$('#emptyCheckbox').show();
	});

	$('#emptyCheckbox').on('click', function () {
		$(this).hide();
		$('#checkedCheckbox').show();
	});

	$('[class^="fas fa-thermometer"]').on('click', function () {
		$('[class^="fas fa-thermometer"]').removeClass('snipswatchActiveVerbosity');
		$(this).addClass('snipswatchActiveVerbosity');
		$.ajax({
			url: '/snipswatch/verbosity',
			data: {
				verbosity: $(this).data('verbosity')
			},
			type: 'POST'
		});
	});

	setInterval(function () {
		refreshData();
	}, 500);
});