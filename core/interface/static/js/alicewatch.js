$(function () {

	function onMessage(msg) {
		let container = $('#console');
		let payload = JSON.parse(msg.payloadString);

		let pattern = /!\[(Red|Green|Yellow|Orange|Blue|Grey)\]\((.*?)\)/gi;
		let text = payload['text'].replace(pattern, '<span class="log$1">$2</span>');

		pattern = /\*\*(.*?)\*\*/gi;
		text = text.replace(pattern, '<span class="logBold">$1</span>');

		pattern = /__(.*?)__/gi;
		text = text.replace(pattern, '<span class="logUnderlined">$1</span>');

		pattern = /--(.*?)--/gi;
		text = text.replace(pattern, '<span class="logDim">$1</span>');

		container.append(
			'<span class="logLine">' + text + '</span>'
		);

		if ($('#checkedCheckbox').is(':visible')) {
			container.scrollTop(container.prop('scrollHeight'));
		}
	}

	function onConnect() {
		MQTT.subscribe('projectalice/logging/alicewatch')
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

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
