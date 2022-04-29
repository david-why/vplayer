# ----------------------------
# Makefile Options
# ----------------------------

NAME := VPLAYER
DESCRIPTION := "Video player"
COMPRESSED := NO
ARCHIVED := YES
VERSION := 1.0.0

HAS_PRINTF := NO

CFLAGS := -Wall -Wextra -Oz -DVPLAYER_VERSION=$(VERSION)
CXXFLAGS := -Wall -Wextra -Oz -DVPLAYER_VERSION=$(VERSION)

# ----------------------------

ifndef CEDEV
$(error CEDEV environment path variable is not set)
endif

include $(CEDEV)/meta/makefile.mk
