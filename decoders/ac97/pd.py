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
# - Split slot values into audio samples of their respective width and
#   frequency (either on user provided parameters, or from inspection of
#   decoded register access).
# - Factor out common code to reduce redundancy:
#   - Reserved bit/bits checks, associated warnings when not zero.
# - Emit annotations for reserved bits only when they are non-zero? To
#   reduce clutter in the bit field rows, and make non-reserved fields
#   stand out more prominently?
#
# Implementor's notes:
# $ cd .../sigrok-dumps
# $ env SIGROKDECODE_DIR=../libsigrokdecode/decoders pulseview -i ac97-data.srzip -l 4
# $ env SIGROKDECODE_DIR=../libsigrokdecode/decoders sigrok-cli -i ac97-data.srzip -l 4 -P ac97:out=SDO:in=SDI:clk=BIT_CLK:sync=SYNC

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
        SLOT_OUT_RAW, SLOT_OUT_TAG, SLOT_OUT_ADDR, SLOT_OUT_DATA,
        SLOT_OUT_03, SLOT_OUT_04, SLOT_OUT_05, SLOT_OUT_06,
        SLOT_OUT_07, SLOT_OUT_08, SLOT_OUT_09, SLOT_OUT_10,
        SLOT_OUT_11, SLOT_OUT_IO,
        SLOT_IN_RAW, SLOT_IN_TAG, SLOT_IN_ADDR, SLOT_IN_DATA,
        SLOT_IN_03, SLOT_IN_04, SLOT_IN_05, SLOT_IN_06,
        SLOT_IN_07, SLOT_IN_08, SLOT_IN_09, SLOT_IN_10,
        SLOT_IN_11, SLOT_IN_IO,
        WARN, ERROR,
    ) = range(32)

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
        ('slot-out-raw', 'Output raw value'),
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
        ('slot-in-raw', 'Input raw value'),
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
        ('slots-out-raw', 'Output numbers', (Ann.SLOT_OUT_RAW,)),
        ('slots-out', 'Output slots', (
            Ann.SLOT_OUT_TAG, Ann.SLOT_OUT_ADDR, Ann.SLOT_OUT_DATA,
            Ann.SLOT_OUT_03, Ann.SLOT_OUT_04, Ann.SLOT_OUT_05, Ann.SLOT_OUT_06,
            Ann.SLOT_OUT_07, Ann.SLOT_OUT_08, Ann.SLOT_OUT_09, Ann.SLOT_OUT_10,
            Ann.SLOT_OUT_11, Ann.SLOT_OUT_IO,)),
        ('bits-in', 'Input bits', (Ann.BITS_IN,)),
        ('slots-in-raw', 'Input numbers', (Ann.SLOT_IN_RAW,)),
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

    def putx(self, ss, es, cls, data):
        """Put a (graphical) annotation."""
        self.put(ss, es, self.out_ann, [cls, data])

    def putf(self, frombit, bitcount, cls, data):
        """Put a (graphical) annotation for a frame's bit field."""
        ss = self.frame_ss_list[frombit]
        es = self.frame_ss_list[frombit + bitcount]
        self.putx(ss, es, cls, data)

    # TODO Put Python and binary annotations.

    def __init__(self):
        self.reset()

    def reset(self):
        self.frame_ss_list = None
        self.frame_slot_lens = [0, 16] + [16 + 20 * i for i in range(1, 13)]
        self.frame_total_bits = 256
        self.handle_slots = {
            0: self.handle_slot_00,
            1: self.handle_slot_01,
            2: self.handle_slot_02,
        }

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
        if False:
            # Expensive(?) bits to text to int conversion.
            text = "".join(["{:d}".format(bits[idx]) for idx in range(count)])
            value = int("0b{}".format(text), 2)
        else:
            # Less expensive(?) sum of power-of-two per 1-bit in a position.
            value = sum([2 ** (count - 1 - i) for i in range(count) if bits[i]])
        return value

    def int_to_nibble_text(self, value, bitcount):
        """Convert number to hex digits for given bit count."""
        digits = (bitcount + 3) // 4
        text = "{{:0{:d}x}}".format(digits).format(value)
        return text

    def get_bit_field(self, data, size, off, count):
        shift = size - off - count
        data >>= shift
        mask = (1 << count) - 1
        data &= mask
        return data

    def start_frame(self, ss):
        """Mark the start of a frame."""
        self.frame_ss_list = [ ss, ]
        self.frame_bits_out = []
        self.frame_bits_in = []
        self.frame_slot_data_out = []
        self.frame_slot_data_in = []
        self.have_slots = {
            True: None,
            False: None,
        }

    def handle_slot_dummy(self, slotidx, bitidx, bitcount, is_out, data):
        """Handle slot x, default/fallback handler."""
        if not self.have_slots[is_out]:
            return
        if not self.have_slots[is_out][slotidx]:
            return
        text = self.int_to_nibble_text(data, bitcount);
        anncls = Ann.SLOT_OUT_TAG if is_out else Ann.SLOT_IN_TAG
        self.putf(bitidx, bitcount, anncls + slotidx, [text])

    def handle_slot_00(self, slotidx, bitidx, bitcount, is_out, data):
        """Handle slot 0, TAG."""
        slotpos = self.frame_slot_lens[slotidx]
        fieldoff = 0
        anncls = Ann.SLOT_OUT_TAG if is_out else Ann.SLOT_IN_TAG

        fieldlen = 1
        ready = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        text = [ 'READY: 1', 'READY', 'RDY', 'R', ] if ready else [ 'ready: 0', 'rdy', '-', ]
        self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        fieldoff += fieldlen

        fieldlen = 12
        valid = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        text = [ 'VALID: {:3x}'.format(valid), '{:3x}'.format(valid), ]
        self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        have_slots = [ True, ] + [ False, ] * 12
        for idx in range(12):
            have_slots[idx + 1] = bool(valid & (1 << (11 - idx)))
        self.have_slots[is_out] = have_slots
        fieldoff += fieldlen

        fieldlen = 1
        rsv = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        if rsv == 0:
            text = [ 'RSV: 0', 'RSV', '0', ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        else:
            text = [ 'rsv: 1', 'rsv', '1', ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
            text = [ 'reserved bit error', 'rsv error', 'rsv', ]
            self.putf(slotpos + fieldoff, fieldlen, Ann.ERROR, text)
        fieldoff += fieldlen

        # TODO Will input slot 0 have a Codec ID, or 3 reserved bits?
        fieldlen = 2
        codec = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        text = [ 'CODEC: {:1x}'.format(codec), '{:1x}'.format(codec), ]
        self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        fieldoff += fieldlen

    def handle_slot_01(self, slotidx, bitidx, bitcount, is_out, data):
        """Handle slot 1, command/status address."""
        slotpos = self.frame_slot_lens[slotidx]
        if not self.have_slots[is_out]:
            return
        if not self.have_slots[is_out][slotidx]:
            return
        fieldoff = 0
        anncls = Ann.SLOT_OUT_TAG if is_out else Ann.SLOT_IN_TAG
        anncls += slotidx

        fieldlen = 1
        if is_out:
            is_read = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
            text = [ 'READ', 'RD', 'R', ] if is_read else [ 'WRITE', 'WR', 'W', ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
            # TODO Check for the "atomic" constraint? Some operations
            # involve address _and_ data, which cannot be spread across
            # several frames. Slot 0 and 1 _must_ be provided within the
            # same frame.
        else:
            rsv = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
            if rsv == 0:
                text = [ 'RSV: 0', 'RSV', '0', ]
                self.putf(slotpos + fieldoff, fieldlen, anncls, text)
            else:
                text = [ 'rsv: 1', 'rsv', '1', ]
                self.putf(slotpos + fieldoff, fieldlen, anncls, text)
                text = [ 'reserved bit error', 'rsv error', 'rsv', ]
                self.putf(slotpos + fieldoff, fieldlen, Ann.ERROR, text)
        fieldoff += fieldlen

        fieldlen = 7
        regaddr = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        # TODO Present 0-63 or 0-126 as the address of the 16bit register?
        # Check for even address, warn when odd? Print in hex or dec?
        text = [ 'REG: {:2x}'.format(regaddr), '{:2x}'.format(regaddr), ]
        self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        fieldoff += fieldlen

        fieldlen = 12
        # TODO These 12 bits are reserved for output, but have a meaning
        # for input. The first 10 bits request output data in the next
        # frame for slots 3-12 (low active). The last 2 bits are reserved.
        rsv = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        if rsv == 0:
            text = [ 'RSV: 0', 'RSV', '0', ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        else:
            text = [ 'rsv: {:03x}'.format(rsv), '{:03x}'.format(rsv), ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
            text = [ 'reserved bits error', 'rsv error', 'rsv', ]
            self.putf(slotpos + fieldoff, fieldlen, Ann.ERROR, text)
        fieldoff += fieldlen

    def handle_slot_02(self, slotidx, bitidx, bitcount, is_out, data):
        """Handle slot 2, command/status data."""
        slotpos = self.frame_slot_lens[slotidx]
        if not self.have_slots[is_out]:
            return
        if not self.have_slots[is_out][slotidx]:
            return
        fieldoff = 0
        anncls = Ann.SLOT_OUT_TAG if is_out else Ann.SLOT_IN_TAG
        anncls += slotidx

        fieldlen = 16
        rwdata = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        # TODO Check for zero when operation is a read.
        text = [ 'DATA: {:4x}'.format(rwdata), '{:4x}'.format(rwdata), ]
        self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        fieldoff += fieldlen

        fieldlen = 4
        rsv = self.get_bit_field(data, bitcount, fieldoff, fieldlen)
        if rsv == 0:
            text = [ 'RSV: 0', 'RSV', '0', ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
        else:
            text = [ 'rsv: {:01x}'.format(rsv), '{:01x}'.format(rsv), ]
            self.putf(slotpos + fieldoff, fieldlen, anncls, text)
            text = [ 'reserved bits error', 'rsv error', 'rsv', ]
            self.putf(slotpos + fieldoff, fieldlen, Ann.ERROR, text)
        fieldoff += fieldlen

    # TODO implement other slots
    # - 1: cmd/status addr (check status vs command)
    # - 2: cmd/status data (check status vs command)
    # - 3-11: audio out/in
    # - 12: io control/status (modem GPIO(?))

    def handle_slot(self, slotidx, data_out, data_in):
        """Process a received slot of a frame."""
        func = self.handle_slots.get(slotidx, self.handle_slot_dummy)
        bitidx = self.frame_slot_lens[slotidx]
        bitcount = self.frame_slot_lens[slotidx + 1] - bitidx
        func(slotidx, bitidx, bitcount, True, data_out)
        func(slotidx, bitidx, bitcount, False, data_in)
        return

    def handle_bits(self, ss, es, bit_out, bit_in):
        """Process a received pair of bits."""

        # Emit the bits' annotations. Only interpret the data when we
        # are in a frame (have seen the start of the frame, and don't
        # exceed the expected number of bits in a frame).
        self.putx(ss, es, Ann.BITS_OUT, ["{:d}".format(bit_out)])
        self.putx(ss, es, Ann.BITS_IN, ["{:d}".format(bit_in)])
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

        # Convert bits to integer values. This shall simplify extraction
        # of bit fields in multiple other locations.
        prev_len = self.frame_slot_lens[slot_idx]

        slot_bits = self.frame_bits_out[prev_len:]
        slot_data = self.bits_to_int(slot_bits)
        self.frame_slot_data_out.append(slot_data)
        slot_data_out = slot_data

        slot_bits = self.frame_bits_in[prev_len:]
        slot_data = self.bits_to_int(slot_bits)
        self.frame_slot_data_in.append(slot_data)
        slot_data_in = slot_data

        # Emit simple annotations for the integer values, until upper
        # layer decode stages will be implemented.
        slot_len = have_len - prev_len
        slot_ss = self.frame_ss_list[prev_len]
        slot_es = self.frame_ss_list[have_len]
        slot_text = self.int_to_nibble_text(slot_data_out, slot_len)
        self.putx(slot_ss, slot_es, Ann.SLOT_OUT_RAW, [slot_text])
        slot_text = self.int_to_nibble_text(slot_data_in, slot_len)
        self.putx(slot_ss, slot_es, Ann.SLOT_IN_RAW, [slot_text])

        self.handle_slot(slot_idx, slot_data_out, slot_data_in)

    def decode(self):
        have_reset = self.has_channel(Pins.RESET)

        # Data is sampled at falling CLK edges. Annotations need to span
        # the period between rising edges. SYNC rises one cycle _before_
        # the start of a frame. Grab the earliest SYNC sample we can get
        # and advance to the start of a bit time. Then keep getting the
        # samples and the end of all subsequent bit times.
        prev_sync = [None, None, None]
        pins = self.wait({Pins.BIT_CLK: 'e'})
        if pins[Pins.BIT_CLK] == 0:
            prev_sync[-1] = pins[Pins.SYNC]
            pins = self.wait({Pins.BIT_CLK: 'r'})
        bit_ss = self.samplenum
        while True:
            pins = self.wait({Pins.BIT_CLK: 'f'})
            prev_sync.pop(0)
            prev_sync.append(pins[Pins.SYNC])
            self.wait({Pins.BIT_CLK: 'r'})
            if prev_sync[0] == 0 and prev_sync[1] == 1:
                self.start_frame(bit_ss)
            self.handle_bits(bit_ss, self.samplenum,
                    pins[Pins.DATA_OUT], pins[Pins.DATA_IN])
            bit_ss = self.samplenum
