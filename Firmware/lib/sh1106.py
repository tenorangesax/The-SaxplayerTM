# SH1106 OLED driver (I2C), framebuf-based. Typical for 1.3" 128x64 modules.
# MIT licensed, trimmed-down version for the Saxplayer.
import framebuf
import time


class SH1106_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C, rotate=False):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        self._rotate = rotate
        self.init_display()

    def _cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes((0x80, cmd)))

    def init_display(self):
        for cmd in (
            0xAE,        # display off
            0xD5, 0x80,  # clock divide
            0xA8, self.height - 1,  # multiplex
            0xD3, 0x00,  # display offset
            0x40,        # start line 0
            0xAD, 0x8B,  # charge pump on
            0xA1 if not self._rotate else 0xA0,  # segment remap
            0xC8 if not self._rotate else 0xC0,  # COM scan direction
            0xDA, 0x12,  # COM pins
            0x81, 0xCF,  # contrast
            0xD9, 0xF1,  # precharge
            0xDB, 0x40,  # VCOM detect
            0xA4,        # resume from RAM
            0xA6,        # normal (not inverted)
        ):
            self._cmd(cmd)
        time.sleep_ms(100)
        self._cmd(0xAF)  # display on
        self.fill(0)
        self.show()

    def poweroff(self):
        self._cmd(0xAE)

    def poweron(self):
        self._cmd(0xAF)

    def contrast(self, val):
        self._cmd(0x81)
        self._cmd(val & 0xFF)

    def invert(self, val):
        self._cmd(0xA7 if val else 0xA6)

    def show(self):
        self.show_pages(0, self.pages)

    def show_pages(self, p0, p1):
        # Push only pages [p0, p1). Lets the UI refresh a small band (e.g. the
        # visualizer bars) without redrawing the whole panel -- far less I2C
        # traffic, so the audio loop is starved for much less time.
        # SH1106 RAM is 132 wide; a 128 panel is centered at column offset 2.
        if p0 < 0:
            p0 = 0
        if p1 > self.pages:
            p1 = self.pages
        for page in range(p0, p1):
            self._cmd(0xB0 | page)
            self._cmd(0x02)        # lower column = 2
            self._cmd(0x10)        # upper column = 0
            start = self.width * page
            self.i2c.writevto(self.addr, (b"\x40", self.buffer[start:start + self.width]))
