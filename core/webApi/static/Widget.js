class Mqtt {
	constructor() {
		this.subscribers = {};
		this.topics = new Set();
		this.connected = false;
	}

	parseSettings() {
		this.aliceSettings = JSON.parse(window.sessionStorage.aliceSettings);
	}

	connect() {
		if (window.sessionStorage.aliceSettings) {
			this.parseSettings()
		} else {
			setTimeout(this.connect, 3);
			return;
		}

		this.mqtt = new Paho.MQTT.Client(this.aliceSettings['mqttHost'], Number(this.aliceSettings['mqttPort']), `widgets_${Date.now()}`);
		this.mqtt.onMessageArrived = (msg) => {
			this.onMessage(msg);
		};

		this.mqtt.connect({
			onSuccess: () => {
				this.onConnect();
			},
			onFailure: () => {
				this.onConnectionFailed();
			},
			timeout  : 5
		});
	}

	onConnect() {
		console.log('Mqtt connection for widgets established');
		this.connected = true;

		const self = this
		this.topics.forEach(topic =>
			self.mqtt.subscribe(topic)
		)
	}

	onMessage(message) {
		if (this.subscribers.hasOwnProperty(message.destinationName)) {
			for (const callback of Object.values(this.subscribers[message.destinationName])) {
				callback(message)
			}
		}
	}

	onConnectionFailed() {
		console.error('Mqtt connection for widgets failed');
	}

	subscribe(widgetUid, destinationName, callback) {
		if (!this.subscribers.hasOwnProperty(destinationName)) {
			this.subscribers[destinationName] = {};
		}

		this.subscribers[destinationName][widgetUid] = callback;
		this.topics.add(destinationName);

		if (this.connected) {
			this.mqtt.subscribe(destinationName);
		}
	}

	unsubscribe(widgetUid, destinationName) {
		if (this.subscribers.hasOwnProperty(destinationName)) {
			delete this.subscribers[destinationName][widgetUid];

			if (Object.keys(this.subscribers[destinationName]).length === 0 && this.mqtt.connected) {
				this.mqtt.unsubscribe(destinationName);
				delete this.subscribers[destinationName];
				this.topics.delete(destinationName);
			}
		}
	}
}

class Widget {
	constructor(uid, widgetId) {
		/*
		The uid is dynamically attributed by the UI when the script is loaded. This ensures the uniqueness of the widget main div
		The widget id is the widget database insert id on Alice's main unit
		 */
		this.uid = uid;
		this.widgetId = widgetId;
		this.myDiv = document.querySelector(`[data-ref="${this.constructor.name}_${this.uid}"]`);
	}

	subscribe(destinationName, callback) {
		if (Array.isArray(destinationName)) {
			for (const topic of destinationName) {
				mqtt.subscribe(this.uid, topic, callback.bind(this));
			}
		} else {
			mqtt.subscribe(this.uid, destinationName, callback.bind(this));
		}
	}

	unsubscribe(destinationName) {
		if (Array.isArray(destinationName)) {
			for (const topic of destinationName) {
				mqtt.unsubscribe(this.uid, topic);
			}
		} else {
			mqtt.unsubscribe(this.uid, destinationName);
		}
	}
}


// Prepare que mqtt object for direct access, and connect after only, so Widget can already use it
const mqtt = new Mqtt();
setTimeout(() => {
	mqtt.connect();
}, 1000);
