$(function () {

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

		$.ajax({
			url: '/syslog/connected/',
			type: 'POST'
		})
	}

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
