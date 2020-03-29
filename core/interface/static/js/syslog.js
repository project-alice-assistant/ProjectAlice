$(function () {

	function onMessage(msg) {
		let container = $('#console');
		let json = JSON.parse(msg.payloadString);

		let pattern = /(\[.*])[ ]+/gi;
		let text = json['msg'].replace(pattern, '<span style="display: inline-block; width: 200px;">$1</span>');

		container.append(text);
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
