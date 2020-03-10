let MQTT;
let mqttSubscribers = {};

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
				let host = response.host;
				if (host === 'localhost') {
					host = window.location.hostname;
					MQTT = new Paho.MQTT.Client(host, Number(response.port), 'ProjectAliceInterface');
					MQTT.onMessageArrived = onMessage;
					MQTT.connect({
						onSuccess: onConnect,
						onFailure: onFailure,
						timeout: 5
					});
				}
			} else {
				console.log('Failed fetching MQTT settings')
			}
		}).fail(function () {
			console.log("Coulnd't connect to MQTT")
		});
	}

	connectMqtt();

});
