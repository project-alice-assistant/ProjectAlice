# ProjectAlice
Project Alice is a smart home assistant completly based on [Snips](https://snips.ai) that is modular and extensible. Snips runs entirely offline and therefor **guarantees** your privacy.

To go further we've built on top of Snips to propose some online alternatives and fallbacks, that are all disabled by default.

# Installing
Please follow the wiki: https://github.com/project-alice-powered-by-snips/ProjectAlice/wiki/Installing


# Who made this?
The original code was started end 2015 and several rewrites made it what it is today. It was entirely written by me *Psycho* until the point, where he decided to open it to the world. There's no money asked, no contribution, but as the license states, you should give back what you've been given, share your improvements and addons to the rest of us, in the form of pull requests.

As of may 2019, *Jierka* joined to prepare Alice for a public release, by providing quality code, fresh ideas and insights over the project. At the same time *maxbachmann* joined, at first to translate to german for the release but very quickly adopted the code and started contributing to the refactoring, rewrite and module production.


# How does it run? What's special about it? Isn't it the same as Snips skill server?
Glad you wonder! First things first, it's much more than just a skill server. It's been made very modular, in fact it runs using user developed modules. You won't have to use any console to train your assistant, we have made a way for the creators to share their modules with the language training included, the whole assistant part is automated

Adding new modules is as easy as using either our CLI or a ticketing system. Updates are automatic, so over time the modules will get better and better with the community input to improve utterances and adding more language support.

Project Alice is meant as an event system, everything triggering events that can be used by modules, such as "onHighCO2", "onTemperatureTooCold" and many others!

Alice has her own mood, can use different voices for different users, knows the user talking to her, likes or dislikes people based on their interaction with her. She can automate your home routine by using a customisation module.

That's only a scratch of Project Alice... If you want more, I highly suggest you give it a try


# Project Alice, as in "Resident Evil", isn't that scary?
Ok, yes, I do admit it may sound scary, but you have my word no one will die down here. I really like the red queen in that movie/game serie and I decided to name the assistant Alice, which lead to my project, Project Alice.


# Where does it run?
Well, it's written in Python but it's been made for Snips that is meant for Raspberry and some other platforms such as the respeaker core or the Matrix Creator. So this pretty limits the choices. A raspberry 3, 3b, 3b+, 3A+ or 4 for the main unit is a good choice. You cannot run Snips on a pi zero but pi zero is more than enough for satellites.


# Can we contribute?
Hey, did you read what I wrote a bit higher? You have to! Just kidding but yes, your contributions are more than welcome, be it core side or on the module side. You'll find more about the guidelines on our wiki.


# Other repositories
- [Project Alice Installer](https://github.com/Psychokiller1888/ProjectAliceInstaller)
- [Project Alice Modules](https://github.com/Psychokiller1888/ProjectAliceModules)
- [Project Alice Amazon Polly and Google WaveNet cached TTS speeches](https://github.com/Psychokiller1888/ProjectAliceCachedSpeeches/tree/Amazon-EnUs-Joanna)

- [Donate](https://paypal.me/Psychokiller1888)
