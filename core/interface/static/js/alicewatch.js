$(function () {

	let $console = $('#console');
	let $stopScroll = $('#stopScroll');
	let $startScroll = $('#startScroll');

	function setVerbosity(level) {
		$.ajax({
			url: '/alicewatch/verbosity/',
			data: {
				verbosity: level
			},
			type: 'POST'
		});
	}

	function onMessage(msg) {
		if (msg.topic != 'projectalice/logging/alicewatch' || !msg.payloadString) {
			return;
		}

		let payload = JSON.parse(msg.payloadString);

		let pattern = /!\[(Red|Green|Yellow|Orange|Blue|Grey)]\((.*?)\)/gi;
		let text = payload['text'].replace(pattern, '<span class="log$1">$2</span>');

		pattern = /\*\*(.*?)\*\*/gi;
		text = text.replace(pattern, '<span class="logBold">$1</span>');

		pattern = /__(.*?)__/gi;
		text = text.replace(pattern, '<span class="logUnderlined">$1</span>');

		pattern = /--(.*?)--/gi;
		text = text.replace(pattern, '<span class="logDim">$1</span>');

		pattern = /\n/gi;
		text = text.replace(pattern, '<br>');

		pattern = /(<span class=".*">\[.*]<\/span> \[.*])[ ]+(.*)/gi;
		text = text.replace(pattern, '<span style="display: inline-block; min-width: 270px;">$1</span><span style="display: inline-block">$2</span>');

		$console.append(
			'<span class="logLine">' + text + '</span>'
		);

		if ($stopScroll.is(':visible')) {
			$console.scrollTop($console.prop('scrollHeight'));
		}
	}

	function onConnect() {
		let date = new Date();
		let time = ('0' + date.getHours()).slice(-2) + ':' + ('0' + date.getMinutes()).slice(-2) + ':' + ('0' + date.getSeconds()).slice(-2);
		$console.append(
			'<span class="logLine"><span style="display: inline-block; width: 270px;"><span class="logYellow">[' + time + ']</span> [AliceWatch]</span>Watching on ' + MQTT_HOST + ':' + MQTT_PORT + ' (MQTT)</span>'
		);

		MQTT.subscribe('projectalice/logging/alicewatch')
	}

	$stopScroll.on('click touchstart', function () {
		$(this).hide();
		$startScroll.show();
		return false;
	});

	$startScroll.on('click touchstart', function () {
		$(this).hide();
		$stopScroll.show();
		return false;
	});

	let $thermometers = $('[class^="fas fa-thermometer"]');
	$thermometers.on('click touchstart', function () {
		$('[class^="fas fa-thermometer"]').removeClass('active');
		$(this).addClass('active');
		let level = $(this).data('verbosity');
		setVerbosity(level);
		document.cookie = 'AliceWatch_verbosity=' + level;
		return false;
	});

	let verbosity = getCookie('AliceWatch_verbosity');
	if (verbosity != '') {
		setVerbosity(verbosity);
		$thermometers.removeClass('active');
		$('[data-verbosity="' + verbosity + '"]').addClass('active');
	}

	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
