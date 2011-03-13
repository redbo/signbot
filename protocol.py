# To use this class, I create another class that inherits from it, but
# overloads the send_to_sign method to send the data as a UDP packet.

# Basic usage looks something like this:

#   self.test_reset()
#   self.pause()
#   self.time_sync()
#   self.set_frame_count(3)
#   self.set_text(0, '{y}OH HAI')
#   self.set_text(1, 'I AM {f}THE{/f} SIGN')
#   self.set_text(2, '{0}{ma} {dd}  {12}')
#   self.resume()

# test_reset is called just to make sure the sign isn't in test mode.
# The sign is then paused while updates are being made.

# You use set_frame_count to tell it how many text frames you'd like in your
# playlist, then call set_text for each frame to set its contents.

# In the background, set_frame_count uploads a playlist with entries for files
# named AA-ZZ.  set_text translates the frame id number you give it to the
# corresponding two-letter filename and updates the file's text.

# It supports a rinky-dink markup language for setting colors, flashing, etc
# inside the text.

# I use this in an app that uses the twisted framework to pull data from SNMP
# and the web.  It periodically polls these sources, then calls set_text to
# update the correct frame.

from time import localtime
from re import sub

move_modes = {
    'random': 0x2f,
    'jump_out': 0x30,
    'move_left': 0x31,
    'move_right': 0x32,
    'scroll_left': 0x33,
    'scroll_right': 0x34,
    'move_up': 0x35,
    'move_down': 0x36,
    'scroll_horiz': 0x37,
    'scroll_up': 0x38,
    'scroll_down': 0x39,
    'fold_horiz': 0x3a,
    'fold_vert': 0x3b,
    'scroll_vert': 0x3c,
    'shuttle_horiz': 0x3d,
    'shuttle_vert': 0x3e,
    'peel_left': 0x3f,
    'peel_right': 0x40,
    'shutter_vert': 0x41,
    'shutter_horiz': 0x42,
    'raindrops': 0x43,
    'rand_mosaic': 0x44,
    'twinkling': 0x45,
    'hip_hop': 0x46,
    'radar': 0x47,
    'fan_out': 0x48,
    'fan_in': 0x49,
    'spiral_right': 0x4a,
    'spiral_left': 0x4b,
    'to_corners': 0x4c,
    'from_corners': 0x4d,
    'to_sides': 0x4e,
    'from_sides': 0x4f,
    'out_blocks': 0x50
}

colors = {
    'black': 0x30,
    'red': 0x31,
    'green': 0x32,
    'amber': 0x33,
    'yellow': 0x33,
    'mix_1': 0x34,
    'mix_2': 0x35,
    'mix_3': 0x36,
    'mix_4': 0x37
}

vertical_alignments = {
    'top': 0x31,
    'bottom': 0x32,
    'center': 0x33
}

horizontal_alignments = {
    'center': 0x30,
    'left': 0x31,
    'right': 0x32
}

parse_map = {
    'b': '\x1c\x30', # black
    'r': '\x1c\x31', # red
    'g': '\x1c\x32', # green
    'a': '\x1c\x33', # yellow (amber)
    'y': '\x1c\x33', # yellow
    'm1': '\x1c\x34', # mixed palette 1
    'm2': '\x1c\x35', # mixed palette 2
    'm3': '\x1c\x36', # mixed palette 3
    'm4': '\x1c\x37', # mixed palette 4
    'f': '\x07\x31', # flash
    '/f': '\x07\x30', # stop flashing
    'y2': '\x0b\x25', # year, 2 digits
    'y4': '\x0b\x26', # year, 4 digits
    'mo': '\x0b\x27', # month numeric
    'ma': '\x0b\x28', # month abbreviated
    'dd': '\x0b\x29', # day of month
    'dw': '\x0b\x2b', # day of week (monday, tuesday...)
    'h': '\x0b\x2c', # hour (24-based)
    'mi': '\x0b\x2d', # minute
    's': '\x0b\x2e', # second
    '24': '\x0b\x2f', # time 24-hour
    '12': '\x0b\x30', # time 12-hour
}

class SignProtocol(object):
    def __init__(self, group_addr = 1, unit_addr = 1):
        self.group_addr = group_addr
        self.unit_addr = unit_addr
        self.drive = 'E'
        self.sequence = 1

    # I meant this to be overloaded by descendent
    def send_to_sign(self, data):
        pass

    def set_text(self, id, text, move_in='random', move_out='random',
            color='red', typeset=True, speed=2, vert_align='center',
            horiz_align='center', flash=False, background='black'):
        if isinstance(speed, int) and speed <= 6:
            speed += 0x30
        def parse_codes(match):
            code = match.group(1).lower()[:2].strip()
            if code in ['0', '1', '2', '3', '4']:
                return '\x1a%c' % code # font
            elif code in parse_map:
                return parse_map[code]
            return match.group(0)
        text = sub(r'\{(\w+)\}', parse_codes, text)
        self.send_to_sign((
                #'\x01Z00\x02A\x0f'
                '\x00\x00\x00\x00\x00\x01Z00\x02A\x0f%(drive)cT%(file)s\x06'
                '\x0aI%(move_in)c'    '\x0aO%(move_out)c' '\x0e20004'
                '\x1b0%(typeset)c'    '\x081'             '\x1f%(vert_align)c'
                '\x1e%(horiz_align)c' '\x0f%(speed)c'     '\x1c%(color)c'
                '\x1d%(background)c'  '\x1a1'             '\x07%(flash)c'
                '%(text)s'            '\x04'
            ) % {
                'drive': self.drive,
                'file': '%c%c' % (65 + int(id / 26), 65 + (id % 26)),
                'typeset': typeset and '\x62' or '\x61',
                'vert_align': vertical_alignments[vert_align],
                'horiz_align': horizontal_alignments[horiz_align],
                'move_in': move_modes[move_in],
                'move_out': move_modes[move_out],
                'speed': speed,
                'color': colors[color],
                'background': colors[background],
                'flash': flash and '\x31' or '\x30',
                'text': text
            })

    def send_message(self, command=(4, 0, 0), data = '', hexdata = '',
            length=0):
        is_response = 0
        if hexdata:
            data = [int(hexdata[i * 2] + hexdata[i * 2 + 1], 16)
                            for i in xrange(len(hexdata) / 2)]
        elif isinstance(data, basestring):
            data = [ord(x) for x in data]
        msg = [
            length % 256,        int(length / 256),        0,
            0,                   self.group_addr,          self.unit_addr,
            self.sequence % 256, int(self.sequence / 256), command[0],
            command[1],          command[2],               is_response
        ] + data
        msg_sum = sum(msg)
        checksum1 = msg_sum % 256
        checksum2 = int(msg_sum / 256)
        self.sequence += 1
        self.send_to_sign('U\xa7%c%c%s' %
            (checksum1, checksum2, ''.join([chr(x) for x in msg if x < 256])))

    def reset(self):
        self.send_message((4, 0, 0))

    def test_reset(self):
        self.send_message((3, 9, 0))

    def pause(self):
        self.send_message((4, 1, 0))

    def resume(self):
        self.send_message((4, 2, 0))

    def time_sync(self):
        loc = localtime()
        self.send_message((5, 2, 2), data=
            [int(str(loc[0] % 1000), 16), 32, int(str(loc[1]), 16),
             int(str(loc[2]), 16), int(str(loc[3]), 16), int(str(loc[4]), 16),
             2, 6])

    def redo_settings(self):
        # upload CONFIG.SYS
        self.send_message((2, 2, 6), hexdata='434f4e4649472e53595300008700000'
            '00003010001000000aa555000070000000300030000000000000000400800040'
            'a07002801000000410101f0f00202a8c0001d6f0000550300079705520000000'
            '00000000006000000000000000000000000000001ffffffff00000000000b303'
            '0303030303030303030005ff9de4a9561e34007444953504c415900000080000'
            'a0020003f005d007500a000ba00d000', length=0x87)
        # reset defaults
        self.send_message((7, 0xd, 1), hexdata='%02x3A0000' % ord(self.drive))
        self.send_message((2, 0xc, 0),
            hexdata='aa55%02x01%02x3031000001312f2f330601' % \
            (ord(self.drive), ord(self.drive)), length=16)

    def set_frame_count(self, count):
        # upload new SEQUENT.SYS
        hexdata = '53455155454e542e53595300%02x%02x00000003010001000000' % \
            ((36 * count + 8) % 256, int((36 * count + 8) / 256))
        hexdata += '53510400%02x000000' % count
        for x in range(count):
            filename = '%x%x' % (65 + int(x / 26), 65 + (x % 26))
            hexdata += ('%02x540f7f08200819010101010820081901010101b0000000%s'
                        '00000000000000000000') % (ord(self.drive), filename)
        self.send_message((2, 2, 6), hexdata=hexdata,
            length=(len(hexdata) / 2) - 24)

    def delete_file(self, file_path):
        self.send_message((7, 6, 2), data=file_path)
        self.send_message((7, 6, 4), data=file_path)

