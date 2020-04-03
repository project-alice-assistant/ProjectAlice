$(function () {

	function onMessage(msg) {
		let json = JSON.parse(msg.payloadString);
		addToLogs(json['msg'])
	}

	function addToLogs(msg) {
		let pattern = /(\[.*])[ ]+/gi;
		let text = msg.replace(pattern, '<span style="display: inline-block; width: 230px;">$1</span>');

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

		$.ajax({
			url: '/syslog/connected/',
			type: 'POST'
		})
	}

	for(let i; i + 1; i < logHistory.length) {
		addToLogs(logHistory[i]);
	}

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
