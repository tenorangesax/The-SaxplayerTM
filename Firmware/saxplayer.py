from machine import Pin, I2C, PWM
import ssd1306
import time
import os

#OLED
i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

#Buttons
btn1 = Pin(26, Pin.IN, Pin.PULL_UP)
btn2 = Pin(27, Pin.IN, Pin.PULL_UP)
btn3 = Pin(28, Pin.IN, Pin.PULL_UP)

#Encoder
enc_a = Pin(2, Pin.IN, Pin.PULL_UP)
enc_b = Pin(3, Pin.IN, Pin.PULL_UP)
enc_btn = Pin(4, Pin.IN, Pin.PULL_UP)

#Audio
audio = PWM(Pin(0))
audio.freq(22050)

volume = 20000
current_track = 0
playing = False

files = [f for f in os.listdir() if f.endswith(".wav")]
files.sort()

last_a = enc_a.value()

def read_encoder():
    global last_a, current_track

    a = enc_a.value()
    if a != last_a:
        if enc_b.value() != a:
            current_track += 1
        else:
            current_track -= 1

        current_track %= len(files)

    last_a = a

def draw_menu():
    oled.fill(0)
    oled.text("MP3 Player", 0, 0)

    for i in range(min(4, len(files))):
        idx = (current_track + i) % len(files)
        prefix = ">" if i == 0 else " "
        oled.text(prefix + files[idx][:15], 0, 16 + i*10)

    oled.show()

def play_wav(filename):
    global playing

    try:
        f = open(filename, "rb")

        f.read(44)

        playing = True

        while playing:
            data = f.read(512)
            if not data:
                break

            for byte in data:
                audio.duty_u16(byte << 8)
                time.sleep_us(45) 

                if not btn2.value():
                    pause()

  
                if not btn3.value():
                    playing = False
                    break

        f.close()

    except Exception as e:
        print("Error:", e)

def pause():
    global playing
    playing = False
    time.sleep(0.3)

while True:
    read_encoder()

    if not btn1.value(): 
        play_wav(files[current_track])
        time.sleep(0.3)

    if not btn3.value(): 
        current_track = (current_track + 1) % len(files)
        time.sleep(0.2)

    draw_menu()
    time.sleep(0.05)
