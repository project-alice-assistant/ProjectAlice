let MQTT;
let mqttSubscribers = {};

function connectMqtt() {
	console.log('Connecting to Mqtt server');
	$.post('/home/getMqttConfig/').done(function (answer) {
		let host = answer.host;
		if (host === 'localhost') {
			host = window.location.hostname;
		}

		MQTT = new Paho.MQTT.Client(host, Number(answer.port), 'ProjectAliceInterface');
		let options = {
			timeout: 3,
			onSuccess: onConnect,
			onFailure: onFailure
		};
		MQTT.onMessageArrived = onMessage;
		MQTT.connect(options);
	});
}

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

function mqttRegisterSelf(target, method) {
	if (!mqttSubscribers.hasOwnProperty(method)) {
		mqttSubscribers[method] = [];
	}
	mqttSubscribers[method].push(target);
}

connectMqtt();

