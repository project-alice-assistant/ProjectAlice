let MQTT;
let mqttSubscribers = {};
let MQTT_HOST;
let MQTT_PORT;

function mqttRegisterSelf(target, method) {
	if (!mqttSubscribers.hasOwnProperty(method)) {
		mqttSubscribers[method] = [];
	}
	mqttSubscribers[method].push(target);
}

$(function () {

	function onFailure(msg) {
		console.log('Mqtt connection failed');
	}

	function onConnect(msg) {
		console.log('Mqtt connected');
		dispatchToMqttSubscribers('onConnect', msg);
	}

	function onMessage(msg) {
		dispatchToMqttSubscribers('onMessage', msg);
	}

	function dispatchToMqttSubscribers(method, msg) {
		if (!mqttSubscribers.hasOwnProperty(method)) {
			return;
		}

		for (const func of mqttSubscribers[method]) {
			func(msg);
		}
	}

	function connectMqtt() {
		console.log('Connecting to Mqtt server');
		$.ajax({
			url: '/home/getMqttConfig/',
			type: 'POST'
		}).done(function (response) {
			if (response.success) {
				MQTT_HOST = response.host;
				MQTT_PORT = Number(response.port);
				if (MQTT_HOST === 'localhost') {
					MQTT_HOST = window.location.hostname;
				}
				MQTT = new Paho.MQTT.Client(MQTT_HOST, MQTT_PORT, 'ProjectAliceInterface');
				MQTT.onMessageArrived = onMessage;
				MQTT.connect({
					onSuccess: onConnect,
					onFailure: onFailure,
					timeout: 5
				});
			} else {
				console.log('Failed fetching MQTT settings')
			}
		}).fail(function () {
			console.log("Coulnd't connect to MQTT")
		});
	}

	function onConnected() {
		MQTT.subscribe('projectalice/nlu/trainingStatus');
	}

	function onMessageIn(msg) {
		let payload = JSON.parse(msg.payloadString);
		let $container = $('#aliceStatus');
		if (payload.status == 'training') {
			if ($container.text().length <= 0) {
				$container.text('Nlu training');
			} else {
				let count = ($container.text().match(/\./g) || []).length;
				if (count < 10) {
					$container.text($container.text() + '.');
				} else {
					$container.text('Nlu training.');
				}
			}
		} else if (payload.status == 'failed') {
			$container.text('Nlu training failed...');
		} else if (payload.status == 'done') {
			$container.text('Nlu training done!');
		}
	}

	mqttRegisterSelf(onConnected, 'onConnect');
	mqttRegisterSelf(onMessageIn, 'onMessage');

	connectMqtt();

});
