# Saxplayer™ Firmware (MicroPython)

WAV music player firmware for the Saxplayer board (ESP32-WROOM, SH1106/SSD1306 OLED, microSD, 3 MX switches, EC11 encoder, 3.5mm jack driven by the ESP32's internal DACs).

## Why WAV and not MP3?

The ESP32-WROOM has no hardware audio decoder, and MicroPython is too slow to decode MP3 in real time. Uncompressed WAV streams straight from the SD card to the DACs with almost no CPU work. Convert your music once on your computer (one command, below) and it plays fine.

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

Convert anything (MP3, FLAC, ...) to player-friendly WAV with ffmpeg, then drop it on the SD card (FAT32):

```
ffmpeg -i song.mp3 -ac 1 -ar 16000 -sample_fmt s16 song.wav
```

Mono, 16 kHz, 16-bit is the sweet spot. If playback stutters, drop to `-ar 8000`. 8-bit files (`-sample_fmt u8` → use `-acodec pcm_u8`) also work and decode faster. Stereo files play left-channel-only.

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

## ⚠ Hardware errata (check before assembly!)

Looking at the netlist, the rotary encoder's common pin (C) and switch return (S2) reach GND **only through capacitors C4/C5**. Capacitors block DC, so as designed the encoder can never actually pull GPIO13/14/27 low — turns and pushes won't register.

Fix (either): bridge C4 and C5 with a solder blob / 0Ω resistor, or update the schematic so C and S2 tie directly to GND with the caps in parallel as debounce caps (that's the standard EC11 circuit).

Also note: audio from the internal 8-bit DAC into headphones is lo-fi and quiet-ish by design — fine for a demo/tutorial board. Keep volume moderate; there's no amplifier on the output.
