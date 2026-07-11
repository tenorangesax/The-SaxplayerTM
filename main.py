# Saxplayer(TM) — MicroPython WAV player
#
# Controls:
#   SW1 (up)      - browser: move up      | playing: prev track (tap) / seek back (hold)
#   SW3 (down)    - browser: move down    | playing: next track (tap) / seek fwd (hold)
#   SW2 (select)  - open / play-pause
#   Encoder turn  - volume
#   Encoder push  - back to browser / stop
#
# When a track is playing and no button is touched for a moment, the screen
# switches to an animated audio-level visualizer. Any button wakes the
# transport (progress/volume) view.
import os
import time
import framebuf

try:
    import urandom
except ImportError:              # some ports name it differently
    import random as urandom

from machine import Pin, I2C, SPI

import config
import inputs
from wavplayer import WavPlayer, WavError

# ---------- display ----------
i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA),
          freq=config.I2C_FREQ)

# Scan the I2C bus and report what's out there. This is the quickest way to
# tell whether the OLED circuit is wired correctly: a working 1.3"/0.96"
# module answers at 0x3C (sometimes 0x3D). An empty list => SDA/SCL/power/
# pullup problem, not a firmware problem.
try:
    _found = i2c.scan()
    print("I2C scan:", [hex(a) for a in _found])
    if config.OLED_ADDR not in _found:
        print("  ! OLED addr", hex(config.OLED_ADDR),
              "not found - check SDA=%d SCL=%d wiring, power, pullups"
              % (config.PIN_I2C_SDA, config.PIN_I2C_SCL))
except Exception as e:
    print("I2C scan failed:", e)

if config.OLED_DRIVER == "sh1106":
    from sh1106 import SH1106_I2C as OLED
else:
    from ssd1306 import SSD1306_I2C as OLED


class _NullOLED:
    """Stand-in for a non-responding display so the rest of the player
    (SD, buttons, encoder, playback) still runs headless and can be
    tested over serial while the display is sorted out separately.
    Any drawing call is a harmless no-op."""
    def __getattr__(self, _name):
        return lambda *a, **k: None


HAS_DISPLAY = True
try:
    oled = OLED(config.OLED_WIDTH, config.OLED_HEIGHT, i2c, addr=config.OLED_ADDR)
    print("OLED init OK (driver=%s addr=%s)" % (config.OLED_DRIVER,
                                                hex(config.OLED_ADDR)))
except Exception as e:  # OSError on no-ACK, but catch all so boot never dies
    print("OLED init failed (%r) - running headless; check display/I2C wiring" % (e,))
    HAS_DISPLAY = False
    oled = _NullOLED()

# The visualizer redraws just its band via show_pages() for smoothness. If an
# OLD driver (without that method) is still on the board, fall back to a full
# show() so the bars STILL render instead of crashing the player.
HAS_SHOW_PAGES = hasattr(oled, "show_pages")
print("driver show_pages:", HAS_SHOW_PAGES)


def splash(lines):
    oled.fill(0)
    y = 8
    for ln in lines:
        oled.text(ln[:16], 0, y)
        y += 12
    oled.show()
    # Always mirror to serial so boot is followable even when a display is
    # expected but blank (wrong driver, contrast, or half-working wiring).
    print("[display]", " | ".join(lines))


splash(("Saxplayer TM", "booting..."))

# ---------- SD card ----------
def mount_sd():
    try:
        from machine import SDCard
        sd = SDCard(slot=2, sck=Pin(config.PIN_SD_SCK),
                    mosi=Pin(config.PIN_SD_MOSI), miso=Pin(config.PIN_SD_MISO),
                    cs=Pin(config.PIN_SD_CS))
        os.mount(sd, config.SD_MOUNT)
        return True
    except Exception as e:
        print("SD mount failed:", e)
        return False


def list_tracks():
    try:
        files = [f for f in os.listdir(config.MUSIC_DIR)
                 if f.lower().endswith(".wav") and not f.startswith(".")]
        files.sort()
        return files
    except OSError:
        return []


# ---------- UI ----------
# Visualizer band = bottom 4 display pages (y32..63). Only these pages are
# pushed each animation frame (show_pages) so the audio loop is barely
# interrupted; the static top area is redrawn only when it changes.
_BAR_TOP = 32
_BAR_P0 = 4
_BAR_P1 = 8
_TITLE_Y = 16          # song title: top of blue zone
_ARTIST_Y = 24         # artist line: directly under the title, above the bars


class UI:
    ROWS = 4
    # Settings rows: (label, attribute name). Toggled on the Settings page.
    SETTINGS = (("Bars", "bars_on"), ("Sleep", "screen_off"))

    def __init__(self, player):
        self.player = player
        self.tracks = []
        self.sel = 0                # index of the current/selected TRACK
        self.cursor = 0             # menu highlight: 0 = Settings, 1.. = tracks
        self.mode = "browse"        # "browse", "settings", or "playing"
        self.view = "transport"     # within playing: "transport" or "vis"
        self.dirty = True
        self.sd_ok = False          # True once an SD card is mounted
        self.last_input = 0         # ticks_ms of the last button activity
        self.set_cursor = 0         # highlighted row on the Settings page
        # runtime toggles (defaults from config). bars = idle visualizer;
        # screen_off = turn the display off entirely when idle.
        self.bars_on = (config.IDLE_MODE == "bars")
        self.screen_off = (config.IDLE_MODE == "blank")
        self._last_pos = -1
        self._last_vis = 0
        self._vis_bg = False        # is the visualizer's static area on screen?
        self._N = config.N_BARS
        self.bars = [0] * self._N   # current bar heights (0.._BAR_H)
        self.peaks = [0] * self._N  # slow-falling peak markers
        self._title_fb = None       # pre-rendered 2x-scaled title (blitted)
        self._title_w = 0
        self._title_static = True   # fits on screen -> no scroll needed
        self._title_scroll = 0
        self._title_name = None
        self._artist = "Unknown"

    # ---- helpers ----
    def _cur_name(self):
        if not self.tracks:
            return "?"
        n = self.tracks[self.sel]
        if n.lower().endswith(".wav"):
            n = n[:-4]
        return n

    def wake(self, now):
        """Called on any interaction: show the transport view and reset idle."""
        self.last_input = now
        if self.mode == "playing":
            self.view = "transport"
        self.dirty = True

    def enter_vis(self, now):
        self.view = "vis"
        self._vis_bg = False
        self._last_vis = 0

    def enter_blank(self, now):
        # Dark idle screen: clear once, then never touch the OLED again until a
        # button wakes it -> no I2C traffic to disturb the audio timing.
        self.view = "blank"
        oled.fill(0)
        oled.show()

    def _reset_bars(self):
        for i in range(self._N):
            self.bars[i] = 0
            self.peaks[i] = 0

    # ---- top-level draw (browser + transport; visualizer animates itself) ----
    def draw(self):
        if self.mode == "browse":
            self._draw_browser()
        elif self.mode == "settings":
            self._draw_settings()
        elif self.view == "transport":
            self._draw_transport()
        self.dirty = False

    def _play_glyph(self, x, y, paused):
        if paused:
            oled.fill_rect(x, y, 3, 10, 1)
            oled.fill_rect(x + 5, y, 3, 10, 1)
        else:                       # right-pointing play triangle
            for k in range(6):
                h = 10 - 2 * k
                if h > 0:
                    oled.vline(x + k, y + k, h, 1)

    # ---- browser ----
    def _menu_label(self, idx):
        # idx 0 is always the Settings entry; 1.. map to track names.
        if idx == 0:
            return "\x10 Settings"          # 0x10 renders as a small triangle
        name = self.tracks[idx - 1]
        if name.lower().endswith(".wav"):
            name = name[:-4]
        return name

    def _draw_browser(self):
        oled.fill(0)
        oled.fill_rect(0, 0, 128, 11, 1)          # title bar
        oled.text("SAXPLAYER", 3, 2, 0)
        vol = "%d" % self.player.volume
        oled.text(vol, 128 - len(vol) * 8 - 3, 2, 0)

        total = len(self.tracks) + 1              # +1 for the Settings row
        top = self.cursor - self.ROWS // 2
        if top > total - self.ROWS:
            top = total - self.ROWS
        if top < 0:
            top = 0
        for row in range(min(self.ROWS, total)):
            idx = top + row
            label = self._menu_label(idx)
            y = 14 + row * 12
            if idx == self.cursor:
                oled.fill_rect(0, y - 1, 121, 11, 1)
                oled.text(label[:14], 4, y + 1, 0)
            else:
                oled.text(label[:14], 4, y + 1, 1)

        if not self.tracks:                       # SD hint on the bottom line
            oled.text("Insert SD card" if not self.sd_ok else "No .wav files",
                      0, 54, 1)
        else:
            self._scrollbar(total, top)
        oled.show()
        if not HAS_DISPLAY:
            print("[display] menu cursor=%d sd=%s tracks=%r"
                  % (self.cursor, self.sd_ok, self.tracks))

    def _scrollbar(self, total, top):
        if total <= self.ROWS:
            return
        track_h = 64 - 14
        oled.vline(126, 14, track_h, 1)
        thumb = track_h * self.ROWS // total
        if thumb < 4:
            thumb = 4
        span = total - self.ROWS
        y = 14 + (track_h - thumb) * top // span if span else 14
        oled.fill_rect(124, y, 3, thumb, 1)

    # ---- settings ----
    def open_settings(self, now):
        self.mode = "settings"
        self.set_cursor = 0
        self.last_input = now
        self.dirty = True

    def _draw_settings(self):
        oled.fill(0)
        oled.fill_rect(0, 0, 128, 11, 1)          # title bar
        oled.text("SETTINGS", 3, 2, 0)
        for i in range(len(self.SETTINGS)):
            label, attr = self.SETTINGS[i]
            val = "ON" if getattr(self, attr) else "OFF"
            y = 16 + i * 12
            col = 0 if i == self.set_cursor else 1
            if i == self.set_cursor:
                oled.fill_rect(0, y - 1, 121, 11, 1)
            oled.text(label, 4, y + 1, col)
            oled.text(val, 121 - len(val) * 8 - 4, y + 1, col)
        oled.show()
        if not HAS_DISPLAY:
            print("[display] SETTINGS",
                  [(l, getattr(self, a)) for l, a in self.SETTINGS])

    # ---- transport (now-playing details) ----
    def _draw_transport(self):
        p = self.player
        oled.fill(0)
        oled.text(self._cur_name()[:16], 0, 0, 1)
        oled.hline(0, 10, 128, 1)
        oled.text("PAUSED" if p.paused else "PLAYING", 0, 16, 1)
        self._play_glyph(118, 15, p.paused)
        pos, dur = p.position_s, p.duration_s
        oled.text("%d:%02d / %d:%02d" % (pos // 60, pos % 60,
                                         dur // 60, dur % 60), 0, 30, 1)
        oled.rect(0, 42, 128, 6, 1)               # progress
        if dur:
            w = 128 * pos // dur
            if w > 128:
                w = 128
            oled.fill_rect(0, 42, w, 6, 1)
        oled.text("V", 0, 54, 1)                  # volume
        oled.rect(12, 55, 104, 6, 1)
        oled.fill_rect(12, 55, 104 * p.volume // 100, 6, 1)
        if p.decimate > 1:                        # down-sampled marker
            oled.text("~", 120, 54, 1)
        oled.show()
        self._last_pos = pos
        if not HAS_DISPLAY:
            print("[display] %s %s %d:%02d/%d:%02d vol=%d" % (
                self._cur_name(), "PAUSED" if p.paused else "PLAYING",
                pos // 60, pos % 60, dur // 60, dur % 60, p.volume))

    # ---- visualizer ----
    # Layout: yellow strip (pages 0-1) = time + progress; blue title band
    # (pages 2-3) = track name in normal font, sitting right above the bars;
    # bars fill pages 4-7.
    def _make_title(self, name):
        """Pre-render the name into an off-screen buffer once so each frame
        just blits it (cheap) and long names can scroll smoothly. Falls back
        to plain text if framebuf misbehaves."""
        self._title_name = name
        self._title_scroll = 0
        a = getattr(self.player, "artist", "")
        self._artist = a if a else "Unknown"
        try:
            n = (name or "?")[:32]
            W = len(n) * 8
            fb = framebuf.FrameBuffer(bytearray(W), W, 8, framebuf.MONO_VLSB)
            fb.fill(0)
            fb.text(n, 0, 0, 1)
            self._title_fb = fb
            self._title_w = W
            self._title_static = W <= 128
        except Exception as e:
            print("title fallback:", e)
            self._title_fb = None

    def _draw_title(self):
        oled.fill_rect(0, 16, 128, 16, 0)         # clear blue title band
        if self._title_fb is None:                # fallback: plain centered
            nm = (self._title_name or "?")[:16]
            x = (128 - len(nm) * 8) // 2
            oled.text(nm, x if x > 0 else 0, _TITLE_Y, 1)
        elif self._title_static:                  # fits: center it
            oled.blit(self._title_fb, (128 - self._title_w) // 2, _TITLE_Y)
        else:                                     # long: marquee scroll
            s = self._title_scroll
            span = self._title_w + 24            # name width + gap
            oled.blit(self._title_fb, -s, _TITLE_Y)
            oled.blit(self._title_fb, span - s, _TITLE_Y)
            s += 2
            self._title_scroll = 0 if s >= span else s
        # artist line, centered, directly under the title
        ar = (self._artist or "Unknown")[:16]
        ax = (128 - len(ar) * 8) // 2
        oled.text(ar, ax if ax > 0 else 0, _ARTIST_Y, 1)
        if HAS_SHOW_PAGES:
            oled.show_pages(2, 4)                 # title band = pages 2-3
        else:
            oled.show()

    def _draw_progress(self):
        p = self.player
        pos, dur = p.position_s, p.duration_s
        oled.fill_rect(0, 0, 128, 16, 0)          # yellow strip
        oled.text("%d:%02d / %d:%02d" % (pos // 60, pos % 60,
                                         dur // 60, dur % 60), 0, 0, 1)
        oled.rect(0, 11, 128, 4, 1)
        if dur:
            w = 128 * pos // dur
            if w > 128:
                w = 128
            oled.fill_rect(0, 11, w, 4, 1)
        if HAS_SHOW_PAGES:
            oled.show_pages(0, 2)                 # progress band = pages 0-1
        else:
            oled.show()
        self._last_pos = pos

    def animate(self):
        p = self.player
        if not self._vis_bg:
            oled.fill(0)
            oled.show()
            self._make_title(self._cur_name())
            self._draw_progress()
            self._draw_title()
            self._draw_bars()                     # render current bars once
            self._vis_bg = True
        else:
            if p.position_s != self._last_pos:
                self._draw_progress()             # refresh ~1/sec
            if not self._title_static:
                self._draw_title()                # scroll long titles
        # Freeze the bars while paused -- only animate during playback so a
        # paused track shows a still frame instead of jittering.
        if not p.paused:
            self._update_bars()
            self._draw_bars()

    def _update_bars(self):
        p = self.player
        amp = p.level_peak                        # 0..127
        hf = p.level_hf                           # 0..255
        N = self._N
        for i in range(N):
            w = amp if i < N // 2 else (amp + hf) // 2
            t = w * 32 // 127
            if t > 32:
                t = 32
            t += (urandom.getrandbits(3) - 3) + (i % 3)   # liveliness
            if t < 0:
                t = 0
            elif t > 32:
                t = 32
            if t > self.bars[i]:                  # fast attack
                self.bars[i] = t
            else:                                 # slow release
                self.bars[i] -= 3
                if self.bars[i] < t:
                    self.bars[i] = t
                if self.bars[i] < 0:
                    self.bars[i] = 0
            if self.bars[i] >= self.peaks[i]:
                self.peaks[i] = self.bars[i]
            elif self.peaks[i] > 0:
                self.peaks[i] -= 1

    def _draw_bars(self):
        oled.fill_rect(0, _BAR_TOP, 128, 32, 0)   # clear band
        N = self._N
        slot = 128 // N
        bw = slot - 2 if slot > 2 else 1
        for i in range(N):
            x = i * slot + 1
            h = self.bars[i]
            if h > 0:
                oled.fill_rect(x, 64 - h, bw, h, 1)
            pk = self.peaks[i]
            if pk > 1:
                oled.hline(x, 64 - pk, bw, 1)
        if HAS_SHOW_PAGES:
            oled.show_pages(_BAR_P0, _BAR_P1)
        else:
            oled.show()          # older driver: full push still shows the bars

    # ---- actions ----
    def nav(self, delta, now):
        if self.mode == "settings":
            self.set_cursor = (self.set_cursor + delta) % len(self.SETTINGS)
        else:  # browser: cursor over [Settings] + tracks
            self.cursor = (self.cursor + delta) % (len(self.tracks) + 1)
        self.last_input = now
        self.dirty = True

    def start_track(self, idx, now):
        if not self.tracks:
            return
        self.sel = idx % len(self.tracks)
        path = config.MUSIC_DIR + "/" + self.tracks[self.sel]
        try:
            self.player.load(path)
            self.mode = "playing"
            self.view = "transport"
            self._reset_bars()
            self.last_input = now
        except (WavError, OSError) as e:
            splash(("Can't play:", self.tracks[self.sel][:16], str(e)[:16]))
            time.sleep(2)
            self.mode = "browse"
        self.dirty = True

    def handle(self, ev, now):
        p = self.player
        if ev == inputs.EV_VOL_UP or ev == inputs.EV_VOL_DOWN:
            p.vol_up() if ev == inputs.EV_VOL_UP else p.vol_down()
            self.wake(now)
            return
        if self.mode == "settings":
            if ev == inputs.EV_SELECT:            # toggle the highlighted row
                attr = self.SETTINGS[self.set_cursor][1]
                setattr(self, attr, not getattr(self, attr))
                self.dirty = True
            elif ev == inputs.EV_BACK:            # exit back to the menu
                self.mode = "browse"
                self.dirty = True
        elif self.mode == "browse":
            if ev == inputs.EV_SELECT:
                if self.cursor == 0:              # Settings row
                    self.open_settings(now)
                else:                             # a track
                    self.start_track(self.cursor - 1, now)
            elif ev == inputs.EV_BACK:
                if not self.sd_ok:                # try remount if just inserted
                    self.sd_ok = mount_sd()
                self.tracks = list_tracks()
                if self.cursor > len(self.tracks):
                    self.cursor = 0
                self.dirty = True
        else:  # playing
            if ev == inputs.EV_SELECT:
                p.toggle_pause()
                self.wake(now)
            elif ev == inputs.EV_BACK:
                p.stop()
                self.mode = "browse"
                self.cursor = self.sel + 1        # land on the track we played
                self.dirty = True


# ---------- input polling for press-and-hold on up/down ----------
def _poll_nav(ui, player, inp, st, now):
    for name, held_fn, is_up in (("up", inp.up_held, True),
                                 ("down", inp.down_held, False)):
        s = st[name]
        held = held_fn()
        if held and s["t"] is None:
            if time.ticks_diff(now, s["rel"]) < 30:   # debounce bounce
                continue
            s["t"] = now
            s["last"] = now
            s["seeking"] = False
            if ui.mode == "browse" or ui.mode == "settings":
                ui.nav(-1 if is_up else 1, now)
            else:
                ui.wake(now)
        elif held and s["t"] is not None:
            elapsed = time.ticks_diff(now, s["t"])
            if ui.mode == "playing":
                if elapsed >= config.HOLD_TO_SEEK_MS:
                    s["seeking"] = True
                    if time.ticks_diff(now, s["last"]) >= config.SEEK_TICK_MS:
                        s["last"] = now
                        step = config.SEEK_STEP_START * (1 + elapsed // 1000)
                        if step > config.SEEK_STEP_MAX:
                            step = config.SEEK_STEP_MAX
                        player.seek_seconds(-step if is_up else step)
                        ui.wake(now)
            else:  # browser auto-repeat while held
                if elapsed >= 400 and \
                        time.ticks_diff(now, s["last"]) >= config.BROWSE_REPEAT_MS:
                    s["last"] = now
                    ui.nav(-1 if is_up else 1, now)
        elif (not held) and s["t"] is not None:
            if ui.mode == "playing" and not s["seeking"]:   # short tap = skip
                ui.start_track(ui.sel + (-1 if is_up else 1), now)
            s["t"] = None
            s["seeking"] = False
            s["rel"] = now


# ---------- main ----------
def main():
    player = WavPlayer()
    inp = inputs.Inputs()
    ui = UI(player)

    # Try to mount the SD, but don't block boot if it's missing -- this lets
    # the display, buttons and encoder be verified without a card inserted.
    ui.sd_ok = mount_sd()
    if not ui.sd_ok:
        splash(("No SD card.", "Running anyway.", "Push knob=retry"))
        time.sleep(1)

    ui.tracks = list_tracks()
    ui.cursor = 1 if ui.tracks else 0             # land on first track, not Settings
    now = time.ticks_ms()
    ui.last_input = now
    ui.draw()

    # press/hold bookkeeping for the up + down buttons
    st = {"up": {"t": None, "last": 0, "seeking": False, "rel": 0},
          "down": {"t": None, "last": 0, "seeking": False, "rel": 0}}

    while True:
        now = time.ticks_ms()

        # discrete events (encoder + select); up/down handled by polling below
        while True:
            ev = inp.get_event()
            if ev is None:
                break
            if ev == inputs.EV_UP or ev == inputs.EV_DOWN:
                continue
            ui.handle(ev, now)

        _poll_nav(ui, player, inp, st, now)

        if player.playing and not player.paused:
            if not player.step():                 # track finished -> next
                ui.start_track(ui.sel + 1, now)
            if ui.mode == "playing" and ui.view == "transport" \
                    and player.position_s != ui._last_pos:
                ui.dirty = True
        else:
            time.sleep_ms(8)

        # On idle (playing): Sleep turns the display off (takes priority), else
        # Bars shows the visualizer, else the now-playing view just stays up.
        # A button wakes the now-playing view.
        if ui.mode == "playing" and player.playing and \
                (ui.screen_off or ui.bars_on):
            if ui.view == "transport" and \
                    time.ticks_diff(now, ui.last_input) > config.IDLE_MS:
                if ui.screen_off:
                    ui.enter_blank(now)
                else:
                    ui.enter_vis(now)
            if ui.view == "vis" and \
                    time.ticks_diff(now, ui._last_vis) >= config.VIS_FPS_MS:
                ui._last_vis = now
                try:
                    ui.animate()
                except Exception as e:
                    # Never let a display hiccup freeze playback or the buttons.
                    print("visualizer error:", e)
                    ui.view = "transport"
                    ui.dirty = True

        if ui.dirty:
            ui.draw()


main()
