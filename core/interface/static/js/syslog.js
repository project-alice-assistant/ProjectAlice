$(function () {

	function onMessage(msg) {
		if (msg.topic != 'projectalice/logging/syslog' || !msg.payloadString) {
			return;
		}

		let json = JSON.parse(msg.payloadString);
		addToLogs(json['msg'])
	}

	function addToLogs(msg) {
		let pattern = /(\[.*])[ ]+/gi;
		let text = msg.replace(pattern, '<span style="display: inline-block; min-width: 300px;">$1</span>');

		let container = $('#console');
		container.append(text);
		if ($('#stopScroll').is(':visible')) {
			container.scrollTop(container.prop('scrollHeight'));
		}
	}

	$('#stopScroll').on('click touchstart', function () {
		$(this).hide();
		$('#startScroll').show();
		return false;
	});

	$('#startScroll').on('click touchstart', function () {
		$(this).hide();
		$('#stopScroll').show();
		return false;
	});

	function onConnect() {
		MQTT.subscribe('projectalice/logging/syslog');
	}

	for(let i = 0; i < logHistory.length; i++) {
		addToLogs(logHistory[i]);
	}

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
