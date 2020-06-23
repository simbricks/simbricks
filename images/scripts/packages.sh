DEV_PACKAGES="
build-essential
curl
emacs24-nox
htop
nmon
slurm
tcpdump
unzip
"

ESSENTIAL_PACKAGES="
ntp
nfs-common
iperf
netcat
make
git
pkg-config
libevent-dev
libunwind-dev
autoconf
automake
libtool
g++
libssl-dev
"

if [[ $INSTALL_DEV_PACKAGES  =~ true || $INSTALL_DEV_PACKAGES =~ 1 ||
        $INSTALL_DEV_PACKAGES =~ yes ]]; then
  apt-get -y install $DEV_PACKAGES
fi

apt-get -y install $ESSENTIAL_PACKAGES
