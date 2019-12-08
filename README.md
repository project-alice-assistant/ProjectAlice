[![Maintainability](https://api.codeclimate.com/v1/badges/ab9aa78508dcccc85b12/maintainability)](https://codeclimate.com/github/project-alice-assistant/ProjectAlice/maintainability) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/55399302e9614fb18a354fb9345dff29)](https://www.codacy.com/manual/Psychokiller1888/ProjectAlice?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=project-alice-assistant/ProjectAlice&amp;utm_campaign=Badge_Grade) ![GitHub language count](https://img.shields.io/github/languages/count/Psychokiller1888/ProjectAlice) ![GitHub top language](https://img.shields.io/github/languages/top/Psychokiller1888/ProjectAlice) ![GitHub](https://img.shields.io/github/license/Psychokiller1888/ProjectAlice) [![Documentation Status](https://readthedocs.org/projects/projectalice/badge/?version=latest)](https://projectalice.readthedocs.io/en/latest/?badge=latest) ![Open issues](https://img.shields.io/github/issues-raw/Psychokiller1888/ProjectAlice) ![GitHub contributors](https://img.shields.io/github/contributors/Psychokiller1888/ProjectAlice) ![Discord](https://img.shields.io/discord/579345007518154752)

# ProjectAlice
Project Alice is a smart voice home assistant that is completly modular and extensible. It was first built around Snips therefore runs entirely offline and never sends or shares your voice interactions with anyone, Project Alice **guarantees** your privacy in your home or wherever you’re using Project Alice.

However, as an option, since we've built Project Alice on top of Snips, Project Alice can be configured to use some online alternatives and fall backs (for example, using Amazon or Google’s Text to Speech engines), just like Snips. Since Snips (and the Project Alice team) strongly believe that decisions about your privacy should be made by you and you alone, these options are all disabled by default.

# Installing
Please follow the [wiki](https://github.com/project-alice-assistant/ProjectAlice/wiki/Installing)

# Chat with us and the community
Join us on our [Discord server](https://discord.gg/Jfcj355)


# Who made this?
The original code base was started at the end 2015 and several rewrites made it what it is today. It was entirely written by me *Psycho* until recently, where I decided to make the code openly available to the world. 

In of May 2019, *Jierka* joined the project to prepare Project Alice for a public release by providing quality code, fresh ideas and insights for the project. At the same time *maxbachmann* also joined the project, at first to translate to German for the release, but soon moved beyond his initial commitment and started contributing to the refactoring, rewrite and module production.

If you want to use Project Alice in a non-commercial setting, I’m not asking you for any money, or a financial contribution, but as the license states, you should try to give back for what you've been given; please share your improvements and add-ons to the rest of us, in the form of pull requests.

# How does it run? What's special about it?
Glad you asked! It's been made very modular, in fact it runs using user developed skills. You won't have to use any console to train your assistant, we have made a way for the creators to share their modules with the language training included, the whole assistant part is automated.

Adding new modules is as easy as using either our CLI or a ticketing system. Updates are automatic, so over time the modules will get better and better with the community input to improve utterances and adding more language support.

Project Alice goes far beyond just acting on your voice requests.  Project Alice is meant as an event driven automation system for your home.  Anything that triggers an event (a voice request or a sensor changing states are considered “events” by Project Alice) can be used by modules to drive further interactions.  For example, a sensor indicating "HighCO2" or "TemperatureTooCold" can be used by a module to create interactions (e.g. Alice announcing, “Warning high CO2 Level detected, move to fresh air immediately” or “It seems a bit chilly, would you like me to turn up the heat?”.  The only limits are your imagination!!

Finally, Project Alice has her own mood (which can vary based on your interactions with her), can use different voices for different users, knows which user is talking to her, and even likes or dislikes people based on their interactions with her. She can also automate your home routines by using a customization module (e.g. turn on air conditioning and lights when a sensor indicates it is too hot and the sun has set).

This is only scratching the surface of Project Alice can and will be able to do... If you want more, I highly suggest you give it a try.


# Project Alice, as in "Resident Evil", isn't that scary?
Ok, yes, I do admit if you’re familiar with the game it may sound a bit scary, but you have my word no one will get hurt fighting against the Umbrella Corporation :). Bottom line, I just really like the Red Queen in that movie/game series so I decided to name the voice assistant Alice, and that naturally lead to me calling the project, Project Alice.


# Where does it run?
Well, since it's written in Python, as of now on Linux architecture. This means a Raspberry Pi and some other platforms such as the respeaker core or the Matrix Creator are the best choices for a hardware platform. As for which Raspberry Pi, a raspberry 3, 3b, 3b+, 3A+ or 4 for the main unit are good choices. You cannot run Alice on a pi zero but pi zero is more than enough for satellites. A satellite runs a subset of the Alice platform, and sends and receives interactions to the main unit.
Well, since it's written in Python, as of now on Linux architecture. This means a Raspberry Pi and some other platforms such as the respeaker core or the Matrix Creator are the best choices for a hardware platform. As for which Raspberry Pi, a raspberry 3, 3b, 3b+, 3A+ or 4 for the main unit are good choices. You cannot run Alice on a pi zero but pi zero is more than enough for satellites. A satellite runs a subset of the Alice platform, and sends and receives interactions to the main unit.


# Can we contribute?
Hey, did you skip ahead and not read what I wrote a bit earlier? You have to! Just kidding, but yes, your contributions are more than welcome, be it core side or on the module side. You'll find more about the guidelines on our wiki.

# Copyright
Project Alice ships under GPLv3, it means you are free to use and redistribute our code but are not allowed to use any part of it under a closed license. Give the community back what you've been given!
Regarding third party tools, scripts, material we use, I took care to mention original creators in files and respect their copyright. If something has slept under my supervision know that it was in no case intended and is the result of a mistake and I ask you to contact me directly to solve the issue asap.

# Third party copyrights
If you see or find a copyright breach, feel free to contact us immediately. It is not our intention to steal anyone else's work or plagiarize your work and is just the result of a missunderstanding that we will gladly fix immediately!


# Special thanks and retired official devs
-   May 2019 - November 2019: *Jierka* for the work provided on the core


# Other repositories
-   [Project Alice Installer](https://github.com/Psychokiller1888/ProjectAliceInstaller)
-   [Project Alice Modules](https://github.com/Psychokiller1888/ProjectAliceModules)
-   [Project Alice Amazon Polly and Google WaveNet cached TTS speeches](https://github.com/Psychokiller1888/ProjectAliceCachedSpeeches/tree/Amazon-EnUs-Joanna)

-   [Donate](https://paypal.me/Psychokiller1888)
