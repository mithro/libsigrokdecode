##
## This file is part of the sigrok project.
##
## Copyright (C) 2012 Joel Holdsworth <joel@airwebreathe.org.uk>
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
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

# I2S protocol decoder

import sigrokdecode as srd

# Annotation formats
ANN_HEX = 0

class Decoder(srd.Decoder):
    api_version = 1
    id = 'i2s'
    name = 'I2S'
    longname = 'Integrated Interchip Sound'
    desc = 'I2S is an electrical serial bus interface standard used ' \
        'for connecting digital audio devices together.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['i2s']
    probes = [
        {'id': 'sck', 'name': 'SCK', 'desc': 'Bit clock line'},
        {'id': 'ws', 'name': 'WS', 'desc': 'Word select line'},
        {'id': 'sd', 'name': 'SD', 'desc': 'Serial Data line'},
    ]
    annotations = [
        ['ASCII', 'Annotations in ASCII format'],
    ]

    def __init__(self, **kwargs):
        self.oldsck = 1
        self.oldws = 1
        self.bitcount = 0
        self.data = 0
        self.samplesreceived = 0
        self.start_sample = None
        self.samplenum = -1

    def start(self, metadata):
        self.out_proto = self.add(srd.OUTPUT_PROTO, 'i2s')
        self.out_ann = self.add(srd.OUTPUT_ANN, 'i2s')

    def report(self):
        return 'I2S: %d samples received' % self.samplesreceived

    def decode(self, ss, es, data):
        for samplenum, (sck, ws, sd) in data:

            # Ignore sample if the bit clock hasn't changed.
            if sck == self.oldsck:
                continue

            self.oldsck = sck
            if sck == 0:   # Ignore the falling clock edge
                continue

            self.data = (self.data << 1) | sd
            self.bitcount += 1

            # This was not the LSB unless WS has flipped
            if ws == self.oldws:
                continue

            # Only submit the sample, if we received the beginning of it
            if self.start_sample != None:
                self.samplesreceived += 1
                self.put(self.start_sample, self.samplenum, self.out_proto,
                    ['data', self.data])
                self.put(self.start_sample, self.samplenum, self.out_ann,
                    [ANN_HEX, ['%s %d-bits: 0x%08x' % ('L' if self.oldws else 'R',
                    self.bitcount, self.data)]])

            # Reset decoder state.
            self.data = 0
            self.bitcount = 0
            self.start_sample = self.samplenum
                
            self.oldws = ws
            