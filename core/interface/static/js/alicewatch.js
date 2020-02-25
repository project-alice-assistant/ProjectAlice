$(function () {
	function refreshData() {
		let container = $('#console');
		$.ajax({
			url: '/alicewatch/refreshConsole/',
			dataType: 'json',
			type: 'POST'
		}).done(function (response) {
			for (let i = 0; i < response.data.length; i++) {
				container.append(
					'<span class="logLine">' + response.data[i] + '</span>'
				);
			}
		}).always(function () {
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
		$('[class^="fas fa-thermometer"]').removeClass('alicewatchActiveVerbosity');
		$(this).addClass('alicewatchActiveVerbosity');
		$.ajax({
			url: '/alicewatch/verbosity/',
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
