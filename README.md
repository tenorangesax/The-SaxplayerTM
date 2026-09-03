# The-Saxplayer™
The Saxplayer™ is a device that houses a ESP32E for the microcontroller, a OLED display to see what songs are playing, 3 MX-Style keyboard switches for navigation of songs, a rotary encoder switch for adjusting the volume and navigating menus, a micro sd card slot for storing your music, and a audio jack for headphones or output to speakers! Also has a cool case I made along with it!

**FIRMWARE GUIDE AT BOTTOM!**

**[WORKING VIDEO DEMO LINK!!!](https://youtu.be/1pTQ9vNJp9s)**

**FINAL SHOTS:**

<img width="4032" height="2268" alt="IMG_7619" src="https://github.com/user-attachments/assets/b4b06943-7fac-4bd3-ac61-aa88e4c960f0" />
<img width="4032" height="3024" alt="IMG_7595" src="https://github.com/user-attachments/assets/0f017a2d-5bd0-4636-b796-8caef22a2003" />

**THE CASE:**

<img width="4032" height="3024" alt="IMG_7608" src="https://github.com/user-attachments/assets/4a2ee0c1-053b-4d9c-b71c-c71af91c6662" />
<img width="4032" height="3024" alt="IMG_7609" src="https://github.com/user-attachments/assets/9ef69578-5fcc-49c9-9d9b-4129a33604b3" />
<img width="4032" height="3024" alt="IMG_7610" src="https://github.com/user-attachments/assets/f1be34c8-3ae2-4ca0-8aab-dc8ea0c301a6" />


**3D VIEWER:**

<img width="1024" height="582" alt="Back_final" src="https://github.com/user-attachments/assets/ac5ef5e7-c8e6-4056-918b-5217ff58426f" />
<img width="1024" height="582" alt="Front_Final" src="https://github.com/user-attachments/assets/44d0cc21-26c2-4791-9414-cd3ce01752a8" />


**THE SCHEMATIC:**
<img width="1479" height="946" alt="schematic" src="https://github.com/user-attachments/assets/cb34f801-f0a0-4f20-907a-e024a205919c" />

**PCB EDITOR:**
<img width="932" height="389" alt="the components" src="https://github.com/user-attachments/assets/cc252789-7ed4-4566-85f0-8c62cc39ac86" />

**CASE MODELING:**
<img width="1285" height="663" alt="Screenshot 2026-04-18 at 4 40 20 PM" src="https://github.com/user-attachments/assets/b339ce5d-e74f-4c7a-9b3f-5e3e41a5086f" />
<img width="1115" height="701" alt="Screenshot 2026-04-18 at 4 41 53 PM" src="https://github.com/user-attachments/assets/90c0088d-9942-4e6f-b16a-170a50bcf6f0" />
<img width="1115" height="701" alt="Screenshot 2026-04-18 at 4 41 45 PM" src="https://github.com/user-attachments/assets/dbeb5399-4b97-4662-b16c-1732b34e60ba" />
<img width="1115" height="663" alt="Screenshot 2026-04-18 at 4 41 21 PM" src="https://github.com/user-attachments/assets/9a9e935e-7990-4103-b0f3-113f440e5df0" />

**BOM:**

| Item name | Quantity | Single price | Link to purchase | Description |
|---|---:|---:|---|---|
| Cherry MX-compatible PCB switch | 3 | $0.40 | [MechanicalKeyboards](https://mechanicalkeyboards.com/products/cherry-mx-honey-silent-45g-tactile-pcb-mount-switch) | Keyboard switch for the 3 keys |
| Micro SD card socket | 1 | $1.52 | PCBA assembled by JLCPCB | MicroSD push-push SMT socket |
| 1.3in 128x64 I2C OLED display | 1 | $5.27 | [Amazon](https://www.amazon.com/JAMHER-Display-Self-Luminous-Projects-Raspberry/dp/B0F3D2ZQZ4?th=1) | Monochrome OLED display |
| 10k resistor | 4 | $0.02 | [Amazon](https://www.amazon.com/LuminologyPro-1000-Piece-Resistor-25-Value-1%CE%A9-1M%CE%A9/dp/B0F4P352BB) | Through-hole resistor |
| 3.5mm audio jack | 1 | $1.52 | [DigiKey](https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/SJ2-35954A-SMT-TR/6619576) | Right-angle SMT audio jack |
| 10uF capacitor | 1 | $0.10 | [Amazon](https://www.amazon.com/Rubycon-Electrolytic-Capacitor-Aluminum-Capacitors/dp/B0F8C24M5R?s=industrial&th=1) | Polarized capacitor |
| Rotary encoder with push switch | 1 | $4.90 | [Amazon](https://www.amazon.com/WWZMDiB-Encoder-Digital-Potentiometer-Arduino/dp/B0C6Q67V97?s=industrial) | Rotary input control |
| 0.1uF capacitor | 2 | $0.05 | [Amazon](https://www.amazon.com/BOJACK-Capacitor-Multilayer-Monolithic-Assortment/dp/B085RDTCCV?th=1) | Decoupling capacitor |
| 10uF capacitor | 2 | $0.10 | [Amazon](https://www.amazon.com/BOJACK-Capacitor-Multilayer-Monolithic-Assortment/dp/B085RDTCCV?th=1) | Capacitor |
| 4.7k resistor | 2 | $0.02 | [Amazon](https://www.amazon.com/LuminologyPro-1000-Piece-Resistor-25-Value-1%CE%A9-1M%CE%A9/dp/B0F4P352BB) | Pull-up / signal resistor |
| ESP32 DevKitC board | 1 | $10.00 | [Amazon](https://www.amazon.com/HiLetgo-ESP-WROOM-32-Development-Microcontroller-Integrated/dp/B0718T232Z?s=industrial) | Main controller board |


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


