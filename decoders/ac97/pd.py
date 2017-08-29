##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2017 Tim 'mithro' Ansell <mithro@mithis.com>
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

import sigrokdecode as srd
from collections import namedtuple

'''
'''

class ChannelError(Exception):
    pass

class Decoder(srd.Decoder):
    api_version = 3
    id = 'ac97'
    name = 'AC\'97'
    longname = 'Audio Codec \'97'
    desc = 'Data from AC\'97 digital controller to AC\'97 analog codec.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['ac97']
    channels = (
        {'id': 'sync', 'name': 'SYNC', 'desc': 'Synchronization signal'},
        {'id': 'clk', 'name': 'CLK', 'desc': 'Bit Clock (12.288MHz)'},
        {'id': 'sdo', 'name': 'SDO', 'desc': 'Serial data from controller to codec (data output)'},
        {'id': 'sdi', 'name': 'SDI', 'desc': 'Serial data from codec to controller (data input)'},
    )
    SYNC = 0
    CLK = 1
    SDO = 2
    SDI = 3

    optional_channels = ()
    options = ()
    annotations = (
        # Slot 0 - TAG
        # Slot 1 - CMD ADDR
        # Slot 2 - CMD DATA
        # Slot 3 - 
        ('bitnum',    'Bit Number'),
        ('sdo-slots', 'Output Slots'),
        ('sdo-tag',   'Tag'),
        ('sdo-addr',  'Address'),
        ('sdo-data',  'Data'),
        ('sdo-slot03', 'Slot 3'),
        ('sdo-slot04', 'Slot 4'),
        ('sdo-slot05', 'Slot 5'),
        ('sdo-slot06', 'Slot 6'),
        ('sdo-slot07', 'Slot 7'),
        ('sdo-slot08', 'Slot 8'),
        ('sdo-slot09', 'Slot 9'),
        ('sdo-slot10', 'Slot 10'),
        ('sdo-slot11', 'Slot 11'),
        ('sdo-slot12', 'Slot 12'),
        ('sdi-slots', 'Input Slots'),
        ('sdi-tag',   'Tag'),
        ('sdi-addr',  'Address'),
        ('sdi-data',  'Data'),
        ('sdi-slot03', 'Slot 3'),
        ('sdi-slot04', 'Slot 4'),
        ('sdi-slot05', 'Slot 5'),
        ('sdi-slot06', 'Slot 6'),
        ('sdi-slot07', 'Slot 7'),
        ('sdi-slot08', 'Slot 8'),
        ('sdi-slot09', 'Slot 9'),
        ('sdi-slot10', 'Slot 10'),
        ('sdi-slot11', 'Slot 11'),
        ('sdi-slot12', 'Slot 12'),
    )
    annotation_rows = (
        ('bit-num',   'Bit Number', (0,)),
        ('sdo-slots', 'Output Slots', tuple(i+1 for i in range(0, 13))),
#        ('sdi-slots', 'Input Slots', range(1+1+12+1,1+1+12+1+12+1)),
    )

    def __init__(self):
        pass

    def metadata(self, key, value):
        pass

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode(self):
        # Make sure we start outside a sync pulse
        self.wait({self.SYNC: 'l'})

        # Search for the start of the sync pulse
        self.wait({self.SYNC: 'h', self.CLK: 'r'})

        while True:
            bit_start = self.samplenum

            slots_valid = []
            address = None
            command = None

            slot_start = -1
            slot_end = -1
            slot_num = -1
            slot_outdata = None
            slot_indata = None
            for i in range(0, 256):
                # Wait for the clock to be high
                sync, clk, sdo, sdi = self.wait({self.CLK: 'h'})
                if i in [0,]+[j+16 for j in range(0, 20*12, 20)]:
                    slot_start = self.samplenum
                    slot_outdata = []
                    slot_indata = []
                    slot_num += 1
                slot_outdata.append(sdo)

                # Wait for clock to be low to sample sdi
                sync, clk, sdo, sdi = self.wait({self.CLK: 'l'})
                slot_indata.append(sdi)

                # Wait for the clock to go from low to high again
                self.wait({self.CLK: 'r'})

                # Annotate the bit number
                self.put(bit_start, self.samplenum, self.out_ann, [0, ["%i" % i]])
                bit_start = self.samplenum

                # Annotate the slot info
                if i in [j+15 for j in range(0, 256, 20)]:
                    slot_end = self.samplenum
                    self.put(
                        slot_start, slot_end, self.out_ann,
                        [1+slot_num, ["Slot %i" % slot_num, "S%i" % slot_num]])
                else:
                    continue

                # Slot 0 is a special thing called the "TAG" it only has 16
                # values, while all the others have 20.
                if slot_num == 0:
                    assert len(slot_outdata) == 16
                    slot_outdata.reverse()
                    # Is this frame valid?
                    frame_valid = slot_outdata[15]
                    # Which slots have valid data?
                    slots_valid = list(slot_outdata[3:])
                    assert len(slots_valid) == 13
                    slots_valid.reverse()
                    assert slot_outdata[2] == 0
                    codec_id = (1 * slot_outdata[0]) + (2 * slot_outdata[1])

                    print("tag(%s): valid:%i slots:%r" % (codec_id, frame_valid, slots_valid))
                    continue

                assert len(slot_outdata) == 20
                # Does the slot have valid data?
                if slots_valid[slot_num] != 1:
                    continue

                print(slot_num, slot_outdata)

                # Command slot
                if slot_num == 1:
                    pass
                # Address slot
                elif slot_num == 2:
                    pass
                # GPIO slot or PCM data?
                elif slot_num == 12:
                    pass
                # PCM audio data
                else:
                    pass

