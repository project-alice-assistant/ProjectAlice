$(function () {

	function onMessage(msg) {
		let container = $('#console');
		let json = JSON.parse(msg.payloadString);

		container.append(json['msg']);
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

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
