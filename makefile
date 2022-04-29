# ----------------------------
# Makefile Options
# ----------------------------

NAME := VPLAYER
DESCRIPTION := "Video player"
COMPRESSED := NO
ARCHIVED := YES
VERSION := "v1.0.0"

HAS_PRINTF := NO

CFLAGS := -Wall -Wextra -Oz -DVPLAYER_VERSION=\"$(VERSION)\"
CXXFLAGS := -Wall -Wextra -Oz -DVPLAYER_VERSION=\"$(VERSION)\"

# ----------------------------

ifndef CEDEV
$(error CEDEV environment path variable is not set)
endif

include $(CEDEV)/meta/makefile.mk

release: bin/VPLAYER.8xp
	tar czvf dist/vplayer-$(VERSION).tgz -C bin VPLAYER.8xp VPLAYER.bin -C .. src
