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

	function onMessage(msg) {
		let container = $('#console');
		let json = JSON.parse(msg.payloadString);

		container.append(json['msg']);

		if ($('#checkedCheckbox').is(':visible')) {
			container.scrollTop(container.prop('scrollHeight'));
		}
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

	function onConnect() {
		MQTT.subscribe('projectalice/logging/syslog');
	}

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
