##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2017 Gerhard Sittig <gerhard.sittig@gmx.net>
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

# This implementation is incomplete. TODO items:
# - Find the most appropriate signal names. Intel uses SDATA_OUT,
#   SDATA_IN, BIT_CLK, SYNC, and RESET#. Mithro's first implementation
#   referred to SDO, SDI, CLK, and SYNC.
# - Support the optional RESET pin, detect cold and warm reset.
# - Split slot values into bit fields, emit respective annotations.

import sigrokdecode as srd

class ChannelError(Exception):
    pass

class Pins:
    (
        DATA_OUT,
        DATA_IN,
        BIT_CLK,
        SYNC,
        RESET,
    ) = range(5)

class Ann:
    (
        BITS_OUT, BITS_IN,
        SLOT_OUT_TAG, SLOT_OUT_ADDR, SLOT_OUT_DATA,
        SLOT_OUT_03, SLOT_OUT_04, SLOT_OUT_05, SLOT_OUT_06,
        SLOT_OUT_07, SLOT_OUT_08, SLOT_OUT_09, SLOT_OUT_10,
        SLOT_OUT_11, SLOT_OUT_IO,
        SLOT_IN_TAG, SLOT_IN_ADDR, SLOT_IN_DATA,
        SLOT_IN_03, SLOT_IN_04, SLOT_IN_05, SLOT_IN_06,
        SLOT_IN_07, SLOT_IN_08, SLOT_IN_09, SLOT_IN_10,
        SLOT_IN_11, SLOT_IN_IO,
        WARN, ERROR,
    ) = range(30)

class Decoder(srd.Decoder):
    api_version = 3
    id = 'ac97'
    name = 'AC \'97'
    longname = 'Audio Codec \'97'
    desc = 'Audio and modem control for PC systems.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['ac97']
    channels = (
        {'id': 'out', 'name': 'SDATA_OUT', 'desc': 'data output'},
        {'id': 'in', 'name': 'SDATA_IN', 'desc': 'data input'},
        {'id': 'clk', 'name': 'BIT_CLK', 'desc': 'data bits clock'},
        {'id': 'sync', 'name': 'SYNC', 'desc': 'frame synchronization'},
    )
    optional_channels = (
        {'id': 'rst', 'name': 'RESET', 'desc': 'reset line'},
    )
    options = (
        # EMPTY
    )
    annotations = (
        ('bits-out', 'Output bits'),
        ('bits-in', 'Input bits'),
        ('slot-out-tag', 'Output TAG'),
        ('slot-out-cmd-addr', 'Output command address'),
        ('slot-out-cmd-data', 'Output command data'),
        ('slot-out-03', 'Output slot 3'),
        ('slot-out-04', 'Output slot 4'),
        ('slot-out-05', 'Output slot 5'),
        ('slot-out-06', 'Output slot 6'),
        ('slot-out-07', 'Output slot 7'),
        ('slot-out-08', 'Output slot 8'),
        ('slot-out-09', 'Output slot 9'),
        ('slot-out-10', 'Output slot 10'),
        ('slot-out-11', 'Output slot 11'),
        ('slot-out-io-ctrl', 'Output I/O control'),
        ('slot-in-tag', 'Input TAG'),
        ('slot-in-sts-addr', 'Input status address'),
        ('slot-in-sts-data', 'Input status data'),
        ('slot-in-03', 'Input slot 3'),
        ('slot-in-04', 'Input slot 4'),
        ('slot-in-05', 'Input slot 5'),
        ('slot-in-06', 'Input slot 6'),
        ('slot-in-07', 'Input slot 7'),
        ('slot-in-08', 'Input slot 8'),
        ('slot-in-09', 'Input slot 9'),
        ('slot-in-10', 'Input slot 10'),
        ('slot-in-11', 'Input slot 11'),
        ('slot-in-io-sts', 'Input I/O status'),
        # TODO add more annotation classes:
        # TAG: 'ready', 'valid', 'id', 'rsv'
        # CMD ADDR: 'r/w', 'addr', 'unused'
        # CMD DATA: 'data', 'unused'
        # 3-11: 'data', 'unused', 'double data'
        ('warn', 'Warnings'),
        ('err', 'Errors'),
    )
    annotation_rows = (
        ('bits-out', 'Output bits', (Ann.BITS_OUT,)),
        ('bits-in', 'Input bits', (Ann.BITS_IN,)),
        ('slots-out', 'Output slots', (
            Ann.SLOT_OUT_TAG, Ann.SLOT_OUT_ADDR, Ann.SLOT_OUT_DATA,
            Ann.SLOT_OUT_03, Ann.SLOT_OUT_04, Ann.SLOT_OUT_05, Ann.SLOT_OUT_06,
            Ann.SLOT_OUT_07, Ann.SLOT_OUT_08, Ann.SLOT_OUT_09, Ann.SLOT_OUT_10,
            Ann.SLOT_OUT_11, Ann.SLOT_OUT_IO,)),
        ('slots-in', 'Input slots', (
            Ann.SLOT_IN_TAG, Ann.SLOT_IN_ADDR, Ann.SLOT_IN_DATA,
            Ann.SLOT_IN_03, Ann.SLOT_IN_04, Ann.SLOT_IN_05, Ann.SLOT_IN_06,
            Ann.SLOT_IN_07, Ann.SLOT_IN_08, Ann.SLOT_IN_09, Ann.SLOT_IN_10,
            Ann.SLOT_IN_11, Ann.SLOT_IN_IO,)),
        ('warn', 'Warnings', (Ann.WARN,)),
        ('err', 'Errors', (Ann.ERROR,)),
    )
    binary = (
        # EMPTY
        # TODO which binary classes to implement?
        # - raw bits? 256 bits of a frame, in/out
        # - audio bits? 20bit per slot, in 24bit units? 3-11 or 1-12?
        #   filtered by TAG bits or all observed? in/out
    )

    def putx(self, ss, es, data):
        """Put a (graphical) annotation."""
        self.put(ss, es, self.out_ann, data)

    # TODO Put Python and binary annotations.

    def __init__(self):
        self.reset()

    def reset(self):
        self.frame_ss_list = None
        self.frame_slot_lens = [0, 16] + [16 + 20 * i for i in range(1, 13)]
        self.frame_total_bits = 256

    def start(self):
        # TODO self.out_python = self.register(srd.OUTPUT_PYTHON)
        # TODO self.out_binary = self.register(srd.OUTPUT_BINARY)
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def bits_to_int(self, bits):
        """Convert MSB-first bit sequence to integer value."""
        if not bits:
            return 0
        count = len(bits)
        value = sum([2 ** (count - 1 - i) for i in range(count) if bits[i]])
        return value

    def int_to_nibble_text(self, value, bitcount):
        """Convert number to hex digits for given bit count."""
        digits = (bitcount + 3) // 4
        text = "{{:0{:d}x}}".format(digits).format(value)
        return text

    def start_frame(self):
        """Mark the start of a frame."""
        self.frame_ss_list = [ self.samplenum, ]
        self.frame_bits_out = []
        self.frame_bits_in = []
        self.frame_slot_data_out = []
        self.frame_slot_data_in = []

    def handle_slot(self, idx, ss, es, data_out, data_in):
        """Process a received slot of a frame."""
        # TODO
        pass

    def handle_bits(self, ss, es, bit_out, bit_in):
        """Process a received pair of bits."""

        # Emit the bits' annotations. Only interpret the data when we
        # are in a frame (have seen the start of the frame, and don't
        # exceed the expected number of bits in a frame).
        self.putx(ss, es, [Ann.BITS_OUT, ["{:d}".format(bit_out)]])
        self.putx(ss, es, [Ann.BITS_IN, ["{:d}".format(bit_in)]])
        if self.frame_ss_list is None:
            return
        if len(self.frame_bits_out) >= self.frame_total_bits:
            return

        # Accumulate the bits within the frame, until one slot of the
        # frame has become available.
        self.frame_ss_list.append(es)
        self.frame_bits_out.append(bit_out)
        self.frame_bits_in.append(bit_in)
        have_len = len(self.frame_bits_out)
        slot_idx = len(self.frame_slot_data_out)
        want_len = self.frame_slot_lens[slot_idx + 1]
        if have_len != want_len:
            return

        # Convert bits to integer values. Emit simple annotations for
        # the integer values, until upper layer decode stages will be
        # implemented.
        prev_len = self.frame_slot_lens[slot_idx]
        slot_len = have_len - prev_len
        slot_ss = self.frame_ss_list[prev_len]
        slot_es = self.frame_ss_list[have_len]

        slot_bits = self.frame_bits_out[prev_len:]
        slot_data = self.bits_to_int(slot_bits)
        slot_text = self.int_to_nibble_text(slot_data, slot_len)
        self.putx(slot_ss, slot_es, [Ann.SLOT_OUT_TAG + slot_idx, [slot_text]])
        self.frame_slot_data_out.append(slot_data)
        slot_data_out = slot_data

        slot_bits = self.frame_bits_in[prev_len:]
        slot_data = self.bits_to_int(slot_bits)
        slot_text = self.int_to_nibble_text(slot_data, slot_len)
        self.putx(slot_ss, slot_es, [Ann.SLOT_IN_TAG + slot_idx, [slot_text]])
        self.frame_slot_data_in.append(slot_data)
        slot_data_in = slot_data

        self.handle_slot(slot_idx, slot_ss, slot_es, slot_data_out, slot_data_in)

    def decode(self):
        have_reset = self.has_channel(Pins.RESET)

        # Data bits get sampled at falling BIT_CLK edges. Data bits need
        # to span the period between rising clock edges in annotations.
        # A frame starts when SYNC is high at the rising(!) edge of the
        # bit clock, and wasn't the last time it got sampled. This is
        # why this implementation:
        # - initially waits for the rising bit clock, and samples SYNC
        # - then waits for the falling bit clock, samples DATA levels,
        #   waits for the rising bit clock, samples SYNC, detects the
        #   start of a frame, and processes the bits just received
        # - keeps repeating that second step until the end of the input
        sync_pins = self.wait({Pins.BIT_CLK: 'r'})
        prev_sync = [0, sync_pins[Pins.SYNC]]
        prev_snum = self.samplenum
        while True:
            data_pins = self.wait({Pins.BIT_CLK: 'f'})
            sync_pins = self.wait({Pins.BIT_CLK: 'r'})
            prev_sync = [prev_sync[1], sync_pins[Pins.SYNC]]
            if prev_sync[0] == 0 and prev_sync[1] == 1:
                self.start_frame()
            self.handle_bits(prev_snum, self.samplenum,
                    data_pins[Pins.DATA_OUT], data_pins[Pins.DATA_IN])
            prev_snum = self.samplenum
