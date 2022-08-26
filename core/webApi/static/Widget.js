/*
 * Copyright (c) 2021
 *
 * This file, Widget.js, is part of Project Alice.
 *
 * Project Alice is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>
 *
 * Last modified: 2021.04.13 at 12:56:49 CEST
 */

class Mqtt {
	constructor() {
		this.subscribers = {}
		this.topics = new Set()
		this.connected = false
	}


	parseSettings() {
		this.aliceSettings = JSON.parse(window.sessionStorage.aliceSettings)
	}


	connect() {
		if (window.sessionStorage.aliceSettings) {
			this.parseSettings()
		} else {
			setTimeout(this.connect, 3)
			return
		}

		this.mqtt = new Paho.MQTT.Client(this.aliceSettings['mqttHost'], Number(this.aliceSettings['mqttPort']), `widgets_${Date.now()}`)
		this.mqtt.onMessageArrived = (msg) => {
			this.onMessage(msg)
		}

		this.mqtt.connect({
			onSuccess: () => {
				this.onConnect()
			},
			onFailure: () => {
				this.onConnectionFailed()
			},
			timeout: 5
		})
	}


	onConnect() {
		console.log('Mqtt connection for widgets established')
		this.connected = true

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
		console.error('Mqtt connection for widgets failed')
	}


	subscribe(widgetUid, destinationName, callback) {
		if (!this.subscribers.hasOwnProperty(destinationName)) {
			this.subscribers[destinationName] = {}
		}

		this.subscribers[destinationName][widgetUid] = callback
		this.topics.add(destinationName)

		if (this.connected) {
			this.mqtt.subscribe(destinationName)
		}
	}


	unsubscribe(widgetUid, destinationName) {
		if (this.subscribers.hasOwnProperty(destinationName)) {
			delete this.subscribers[destinationName][widgetUid]

			if (Object.keys(this.subscribers[destinationName]).length === 0 && this.mqtt.connected) {
				this.mqtt.unsubscribe(destinationName)
				delete this.subscribers[destinationName]
				this.topics.delete(destinationName)
			}
		}
	}
}


class Widget {

	TOPIC_ASR_START_LISTENING              = 'hermes/asr/startListening'
	TOPIC_ASR_STOP_LISTENING               = 'hermes/asr/stopListening'
	TOPIC_ASR_TOGGLE_OFF                   = 'hermes/asr/toggleOff'
	TOPIC_ASR_TOGGLE_ON                    = 'hermes/asr/toggleOn'
	TOPIC_AUDIO_FRAME                      = 'hermes/audioServer/{}/audioFrame'
	TOPIC_CONTINUE_SESSION                 = 'hermes/dialogueManager/continueSession'
	TOPIC_DIALOGUE_MANAGER_CONFIGURE       = 'hermes/dialogueManager/configure'
	TOPIC_END_SESSION                      = 'hermes/dialogueManager/endSession'
	TOPIC_HOTWORD_DETECTED                 = 'hermes/hotword/default/detected'
	TOPIC_HOTWORD_TOGGLE_OFF               = 'hermes/hotword/toggleOff'
	TOPIC_HOTWORD_TOGGLE_ON                = 'hermes/hotword/toggleOn'
	TOPIC_INTENT_NOT_RECOGNIZED            = 'hermes/dialogueManager/intentNotRecognized'
	TOPIC_INTENT_PARSED                    = 'hermes/nlu/intentParsed'
	TOPIC_NLU_ERROR                        = 'hermes/error/nlu'
	TOPIC_NLU_INTENT_NOT_RECOGNIZED        = 'hermes/nlu/intentNotRecognized'
	TOPIC_NLU_QUERY                        = 'hermes/nlu/query'
	TOPIC_PARTIAL_TEXT_CAPTURED            = 'hermes/asr/partialTextCaptured'
	TOPIC_PLAY_BYTES                       = 'hermes/audioServer/{}/playBytes/#'
	TOPIC_PLAY_BYTES_FINISHED              = 'hermes/audioServer/{}/playFinished'
	TOPIC_SESSION_ENDED                    = 'hermes/dialogueManager/sessionEnded'
	TOPIC_SESSION_QUEUED                   = 'hermes/dialogueManager/sessionQueued'
	TOPIC_SESSION_STARTED                  = 'hermes/dialogueManager/sessionStarted'
	TOPIC_START_SESSION                    = 'hermes/dialogueManager/startSession'
	TOPIC_SYSTEM_UPDATE                    = 'hermes/leds/systemUpdate'
	TOPIC_HLC_CLEAR_LEDS                   = 'hermes/leds/clear'
	TOPIC_TEXT_CAPTURED                    = 'hermes/asr/textCaptured'
	TOPIC_TOGGLE_FEEDBACK                  = 'hermes/feedback/sound/toggle{}'
	TOPIC_TOGGLE_FEEDBACK_OFF              = 'hermes/feedback/sound/toggleOff'
	TOPIC_TOGGLE_FEEDBACK_ON               = 'hermes/feedback/sound/toggleOn'
	TOPIC_TTS_FINISHED                     = 'hermes/tts/sayFinished'
	TOPIC_TTS_SAY                          = 'hermes/tts/say'
	TOPIC_VAD_DOWN                         = 'hermes/voiceActivity/{}/vadDown'
	TOPIC_VAD_UP                           = 'hermes/voiceActivity/{}/vadUp'
	TOPIC_WAKEWORD_DETECTED                = 'hermes/hotword/{}/detected'

	constructor(uid, widgetId) {
		/*
		The uid is dynamically attributed by the UI when the script is loaded. This ensures the uniqueness of the widget main div
		The widget id is the widget database insert id on Alice's main unit
		 */
		this.uid = uid
		this.widgetId = widgetId
		this.myDiv = document.querySelector(`[data-ref="${this.constructor.name}_${this.uid}"]`)

		this.aliceSettings = JSON.parse(window.sessionStorage.aliceSettings)
		let self = this
		this.mySkill = new Proxy({}, {
			get: function (target, property, receiver) {
				return function () {
					const args = arguments[0] || {}
					return fetch(`http://${self.aliceSettings['aliceIp']}:${self.aliceSettings['apiPort']}/api/v1.0.1/widgets/${self.widgetId}/function/${property}/`, {
						method:  'POST',
						body:    JSON.stringify(args),
						headers: {
							'auth':         localStorage.getItem('apiToken'),
							'content-type': 'application/json'
						}
					})
				}
			}
		})
	}


	subscribe(destinationName, callback) {
		if (Array.isArray(destinationName)) {
			for (const topic of destinationName) {
				mqtt.subscribe(this.uid, topic, callback.bind(this))
			}
		} else {
			mqtt.subscribe(this.uid, destinationName, callback.bind(this))
		}
	}


	unsubscribe(destinationName) {
		if (Array.isArray(destinationName)) {
			for (const topic of destinationName) {
				mqtt.unsubscribe(this.uid, topic)
			}
		} else {
			mqtt.unsubscribe(this.uid, destinationName)
		}
	}
}


// Prepare que mqtt object for direct access, and connect after only, so Widget can already use it
const mqtt = new Mqtt()
setTimeout(() => {
	mqtt.connect()
}, 1000)
