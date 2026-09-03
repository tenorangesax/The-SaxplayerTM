# Saxplayer™ Firmware (MicroPython)

WAV music player firmware for the Saxplayer board (ESP32-WROOM, SH1106/SSD1306 OLED, microSD, 3 MX switches, EC11 encoder, 3.5mm jack driven by the ESP32's internal DACs).


## Flashing

1. Install [esptool](https://docs.micropython.org/en/latest/esp32/tutorial/intro.html) and grab the latest ESP32 MicroPython firmware from micropython.org/download/ESP32_GENERIC/
2. Flash it (adjust the port):
   ```
   esptool.py --chip esp32 --port /dev/tty.usbserial-XXXX erase_flash
   esptool.py --chip esp32 --port /dev/tty.usbserial-XXXX write_flash -z 0x1000 ESP32_GENERIC-*.bin
   ```
3. Copy this Firmware folder's `.py` files to the board with [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):
   ```
   mpremote cp boot.py config.py inputs.py wavplayer.py main.py :
   mpremote mkdir lib
   mpremote cp lib/sh1106.py lib/ssd1306.py :lib/
   mpremote reset
   ```

## Preparing music

Convert anything (MP3, FLAC, ...) to player readable WAV with ffmpeg, then drop it on the SD card (FAT32):

```
ffmpeg -i song.mp3 -ac 1 -ar 16000 -sample_fmt s16 song.wav
```

Mono, 16 kHz, 16-bit is prefered.
## Controls

| Input | Browser | Now playing |
|---|---|---|
| SW1 (up) | move up | previous track |
| SW3 (down) | move down | next track |
| SW2 (select) | play | play / pause |
| Encoder turn | volume | volume |
| Encoder push | rescan SD | stop, back to browser |

## Files

- `config.py` — every pin assignment and tunable, matches the KiCad netlist
- `inputs.py` — IRQ-driven buttons + quadrature encoder decoding
- `wavplayer.py` — WAV parsing and DAC playback (viper-optimized conversion)
- `main.py` — SD mount, file browser, now-playing UI
- `lib/sh1106.py`, `lib/ssd1306.py` — OLED drivers (1.3" panels are usually SH1106; switch with `OLED_DRIVER` in config.py)

## Hardware errors (check before assembling!)

The rotary encoder's common pin (C) and switch return (S2) reach GND **only through capacitors C4/C5**. Capacitors block DC, so as designed the encoder can never actually pull GPIO13/14/27 low, so turns and pushes won't register.

It would already be bridged for you by me, but if not, bridge C4 and C5 with a solder blob/0Ω resistor.


