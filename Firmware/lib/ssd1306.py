# SSD1306 OLED driver (I2C), framebuf-based. From micropython-lib (MIT), trimmed.
import framebuf


class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        self.init_display()

    def _cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes((0x80, cmd)))

    def init_display(self):
        for cmd in (
            0xAE,        # display off
            0x20, 0x00,  # horizontal addressing
            0x40,        # start line 0
            0xA1,        # segment remap
            0xA8, self.height - 1,  # multiplex
            0xC8,        # COM scan direction
            0xD3, 0x00,  # display offset
            0xDA, 0x12 if self.height == 64 else 0x02,  # COM pins
            0xD5, 0x80,  # clock divide
            0xD9, 0xF1,  # precharge
            0xDB, 0x30,  # VCOM detect
            0x81, 0xFF,  # contrast
            0xA4,        # resume from RAM
            0xA6,        # normal (not inverted)
            0x8D, 0x14,  # charge pump on
            0xAF,        # display on
        ):
            self._cmd(cmd)
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
        if p0 < 0:
            p0 = 0
        if p1 > self.pages:
            p1 = self.pages
        if p1 <= p0:
            return
        self._cmd(0x21)  # column range
        self._cmd(0)
        self._cmd(self.width - 1)
        self._cmd(0x22)  # page range
        self._cmd(p0)
        self._cmd(p1 - 1)
        start = p0 * self.width
        end = p1 * self.width
        self.i2c.writevto(self.addr, (b"\x40", self.buffer[start:end]))
