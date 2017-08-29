##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2012 Uwe Hermann <uwe@hermann-uwe.de>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

'''
The AC97 (Audio Codec '97;also MC'97 for Modem Codec '97) protocol decoder
supports decoding the AC'97 signal between the digital controller and the audio
or modem codec (which contains the analog components of the architecture.

AC'97 defines a high-quality, 16- or 20-bit audio architecture with 5.1
surround sound support for the PC. AC'97 supports a 96 kHz sampling rate at
20-bit stereo resolution and a 48 kHz sampling rate at 20-bit stereo resolution
for multichannel recording and playback.

See https://en.wikipedia.org/wiki/AC%2797 for more information.
'''

from .pd import Decoder
