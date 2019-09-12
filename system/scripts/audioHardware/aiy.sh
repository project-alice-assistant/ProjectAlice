cd ~
git clone https://github.com/google/aiyprojects-raspbian.git
cd aiyprojects-raspbian
git checkout voicekit
scripts/configure-driver.sh
scripts/install-alsa-config.sh