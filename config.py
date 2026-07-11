# Saxplayer(TM) hardware configuration
# Pin map extracted from PCB/Saxplayer.kicad_pcb — do not change unless the board changes.

# --- OLED (0.96" 128x64, I2C) ---
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22
I2C_FREQ = 400_000
OLED_ADDR = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64
# 1.3" modules are usually SH1106, 0.96" are SSD1306. Flip this if the
# display looks shifted/garbled -- or stays blank (wrong charge-pump cmd).
# Board is populated with a 0.96" module, which is SSD1306.
OLED_DRIVER = "ssd1306"  # "sh1106" or "ssd1306"

# --- microSD (SPI) ---
PIN_SD_CS = 5
PIN_SD_SCK = 18
PIN_SD_MOSI = 23
PIN_SD_MISO = 19
SD_MOUNT = "/sd"
MUSIC_DIR = "/sd"  # where to look for .wav files

# --- Buttons (active low, to GND) ---
PIN_BTN_UP = 32     # SW1
PIN_BTN_SELECT = 33 # SW2 (play/pause/select)
PIN_BTN_DOWN = 34   # SW3 (GPIO34 is input-only; board has external 10k pullup R6)

# --- Rotary encoder (EC11) ---
PIN_ENC_A = 14
PIN_ENC_B = 13
PIN_ENC_SW = 27  # push = back

# --- Audio (internal 8-bit DACs, cap-coupled to 3.5mm jack) ---
PIN_DAC_L = 25  # tip
PIN_DAC_R = 26  # ring

# --- Player defaults ---
VOLUME_DEFAULT = 60      # 0..100
VOLUME_STEP = 5
CHUNK_MS = 40            # audio chunk size; UI is serviced between chunks
DEBOUNCE_MS = 200

# Highest per-second sample rate the software DAC loop can hold cleanly.
# Files above this are automatically decimated (every Nth sample) so they
# still play at the CORRECT PITCH instead of dragging slow. 16 kHz mono is
# the recommended source format; higher-rate files still work, just softer.
MAX_PLAY_RATE = 22050

# --- UI / interaction ---
IDLE_MS = 2500          # no input this long on the playing screen -> visualizer
HOLD_TO_SEEK_MS = 450   # hold next/prev longer than this = scrub instead of skip
SEEK_TICK_MS = 220      # how often a held seek fires
SEEK_STEP_START = 5     # seconds per seek tick at the start of a hold
SEEK_STEP_MAX = 30      # seconds per seek tick after holding a while (accel)
BROWSE_REPEAT_MS = 140  # list auto-scroll interval when a nav button is held
# Idle screen while a track plays:
#   "blank" -> display goes fully dark (zero I2C traffic = cleanest audio)
#   "bars"  -> animated visualizer (looks great, but refreshing the OLED
#              nibbles at the audio timing loop)
IDLE_MODE = "bars"
N_BARS = 16             # spectrum-ish bars on the idle visualizer
VIS_FPS_MS = 220        # visualizer redraw interval; higher = fewer I2C refreshes
                        # = less audio interference (was 110). Raise further to
                        # ~300 for even cleaner sound, lower for smoother bars.
