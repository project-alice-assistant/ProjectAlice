$(function () {

	function getLogColor(line) {
		if (line.includes('[INFO]')) {
			return 'logInfo';
		} else if (line.includes('[WARNING]')) {
			return 'logWarning';
		} else if (line.includes('[ERROR]')) {
			return 'logError';
		} else {
			return 'logInfo';
		}
	}

	function refreshData(type) {
		let container = $('#console');

		$.get('/syslog/' + type, function (data) {
			for (let i = 0; i < data.data.length; i++) {
				container.append(
					'<span class="logLine ' + getLogColor(data.data[i]) + '">' + data.data[i] + '</span>'
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
	});

	$('#emptyCheckbox').on('click touchstart', function () {
		$(this).hide();
		$('#checkedCheckbox').show();
	});

	refreshData('refresh');

	setInterval(function () {
		refreshData('update');
	}, 500);
});