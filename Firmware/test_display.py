# test_display.py -- standalone OLED test, bypasses SD/inputs entirely.
#
# Run:  mpremote connect /dev/cu.usbserial-XXXX run test_display.py
#
# Why this exists:
#   The OLED can ACK on I2C (0x3C) and accept an init sequence with NO error,
#   yet stay completely black. The usual cause is the charge-pump / DC-DC
#   command: SH1106 uses 0xAD,0x8B; SSD1306 uses 0x8D,0x14. Many "1.3 SH1106"
#   modules actually carry SSD1306 silicon (or the reverse). Send the wrong
#   one and the pixel-drive voltage never turns on -> blank screen.
#
# This script tries BOTH drivers in turn and fills the whole panel white,
# then draws text. Watch the glass: whichever driver lights it up is the one
# you want in config.py (OLED_DRIVER).

import time
from machine import Pin, I2C
import config

i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA),
          freq=config.I2C_FREQ)
print("I2C scan:", [hex(a) for a in i2c.scan()])


def try_driver(name):
    print("\n--- trying driver:", name, "---")
    try:
        if name == "sh1106":
            from sh1106 import SH1106_I2C as OLED
        else:
            from ssd1306 import SSD1306_I2C as OLED
        oled = OLED(config.OLED_WIDTH, config.OLED_HEIGHT, i2c,
                    addr=config.OLED_ADDR)
    except Exception as e:
        print("  init failed:", repr(e))
        return

    # 1) whole panel ON -- easiest thing to see from across the room
    oled.fill(1)
    oled.show()
    print("  full-screen fill sent -- is the WHOLE panel lit white?")
    time.sleep(3)

    # 2) text, so you can confirm addressing/offset is right too
    oled.fill(0)
    oled.text("DRIVER:", 0, 8)
    oled.text(name, 0, 24)
    oled.text("128x64 OK", 0, 44)
    oled.show()
    print("  text sent -- can you read '%s'?" % name)
    time.sleep(4)

    oled.fill(0)
    oled.show()


try_driver("sh1106")
try_driver("ssd1306")
print("\nDone. Put the driver that lit up into config.py -> OLED_DRIVER.")
