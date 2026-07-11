# WAV playback through the ESP32's internal 8-bit DACs (GPIO25/26).
#
# The ESP32-WROOM has no audio decoder, so this plays uncompressed WAV.
# It streams the file from SD in small chunks; between chunks the main
# loop gets control to service the UI. Mono output is written to both
# DACs (tip + ring of the jack), so both ears get sound.
#
# Best results: mono, 8-bit unsigned or 16-bit signed PCM, 8-16 kHz.
# See Firmware/README.md for the ffmpeg one-liner to convert files.
import gc
import time
import micropython
from machine import DAC, Pin

import config

_SILENCE = 128  # midpoint for 8-bit unsigned


@micropython.viper
def _cvt16(src: ptr8, out: ptr8, n: int, bstep: int, vol: int):
    # 16-bit signed LE -> 8-bit unsigned. Reads the first (left) channel of
    # each source frame and advances `bstep` bytes per output sample. bstep =
    # frame_size * decimation, so this handles mono/stereo AND down-sampling
    # of high-rate files in one pass. Scaled by vol (0..256).
    i = 0
    j = 0
    while j < n:
        lo = int(src[i])
        hi = int(src[i + 1])
        s = (hi << 8) | lo
        if s >= 32768:
            s -= 65536
        s = (s * vol) >> 8
        out[j] = ((s >> 8) + 128) & 0xFF
        i += bstep
        j += 1


@micropython.viper
def _cvt8(src: ptr8, out: ptr8, n: int, bstep: int, vol: int):
    # 8-bit unsigned -> 8-bit unsigned with volume. bstep = frame_size * dec.
    i = 0
    j = 0
    while j < n:
        s = int(src[i]) - 128
        s = (s * vol) >> 8
        out[j] = (s + 128) & 0xFF
        i += bstep
        j += 1


@micropython.viper
def _meter(out: ptr8, n: int) -> int:
    # Cheap loudness measure over an already-converted 8-bit chunk. Returns
    # peak deviation (0..127) in the high byte and average sample-to-sample
    # delta (a rough "brightness"/high-freq proxy, 0..255) in the low byte.
    peak = 0
    hf = 0
    prev = 128
    i = 0
    while i < n:
        v = int(out[i])
        d = v - 128
        if d < 0:
            d = -d
        if d > peak:
            peak = d
        e = v - prev
        if e < 0:
            e = -e
        hf += e
        prev = v
        i += 1
    if n > 0:
        hf = hf // n
    if hf > 255:
        hf = 255
    return (peak << 8) | (hf & 0xFF)


class WavError(Exception):
    pass


def _info_artist(buf):
    """Pull the artist (IART) out of a WAV LIST/INFO chunk body, or "" if none.
    Body layout: 'INFO' then repeated [4-byte id][4-byte LE size][bytes(+pad)]."""
    if len(buf) < 4 or buf[0:4] != b"INFO":
        return ""
    i = 4
    n = len(buf)
    while i + 8 <= n:
        sid = buf[i:i + 4]
        sz = int.from_bytes(buf[i + 4:i + 8], "little")
        i += 8
        val = buf[i:i + sz]
        i += sz + (sz & 1)
        if sid == b"IART":
            try:
                return val.split(b"\x00")[0].decode().strip()
            except Exception:
                return ""
    return ""


class WavPlayer:
    def __init__(self):
        self._dac_l = DAC(Pin(config.PIN_DAC_L))
        self._dac_r = DAC(Pin(config.PIN_DAC_R))
        self._file = None
        self.volume = config.VOLUME_DEFAULT  # 0..100
        self.playing = False
        self.paused = False
        self.rate = 0
        self.duration_s = 0
        self.decimate = 1        # >1 when a file is down-sampled to play in tune
        self.level_peak = 0      # 0..127, updated each chunk for the visualizer
        self.level_hf = 0        # 0..255
        self.artist = ""         # from the WAV's LIST/INFO IART tag, if present
        self._silence()

    def _silence(self):
        self._dac_l.write(_SILENCE)
        self._dac_r.write(_SILENCE)

    # ---- WAV header parsing ----
    def load(self, path):
        self.stop()
        f = open(path, "rb")
        try:
            if f.read(4) != b"RIFF":
                raise WavError("not RIFF")
            f.read(4)
            if f.read(4) != b"WAVE":
                raise WavError("not WAVE")
            fmt = None
            data_pos = data_len = 0
            artist = ""
            # Scan every chunk. We DON'T stop at 'data' (we seek past it) so a
            # trailing LIST/INFO tag chunk still gets read for the artist name.
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                cid = hdr[0:4]
                size = int.from_bytes(hdr[4:8], "little")
                if cid == b"fmt ":
                    fmt = f.read(size)
                    if size & 1:
                        f.seek(1, 1)
                elif cid == b"data":
                    data_pos = f.tell()
                    data_len = size
                    f.seek(size + (size & 1), 1)   # skip audio, keep scanning
                elif cid == b"LIST":
                    body = f.read(size)
                    if size & 1:
                        f.seek(1, 1)
                    a = _info_artist(body)
                    if a:
                        artist = a
                else:
                    f.seek(size + (size & 1), 1)
            if not fmt or not data_pos:
                raise WavError("bad WAV")
            audio_fmt = int.from_bytes(fmt[0:2], "little")
            self.channels = int.from_bytes(fmt[2:4], "little")
            self.rate = int.from_bytes(fmt[4:8], "little")
            self.bits = int.from_bytes(fmt[14:16], "little")
            if audio_fmt != 1 or self.bits not in (8, 16):
                raise WavError("need 8/16-bit PCM")
            if self.channels not in (1, 2):
                raise WavError("need mono/stereo")
            # Scanning for the artist tag ran the file pointer to EOF; rewind
            # to the start of the audio so playback reads real samples (not the
            # end of file, which would make every track "finish" instantly).
            f.seek(data_pos)
        except Exception:
            f.close()
            raise

        self._file = f
        self.artist = artist
        self._data_pos = data_pos
        self._data_len = data_len
        self._remaining = data_len
        self._frame_size = self.channels * (self.bits // 8)
        n_frames = data_len // self._frame_size
        self.duration_s = n_frames // self.rate if self.rate else 0

        # Pick a decimation factor so the OUTPUT rate stays within what the
        # software DAC loop can actually sustain. This is what keeps high-rate
        # files (44.1k, 48k) in tune instead of playing slow/low-pitched.
        self.decimate = 1
        while self.rate // (self.decimate + 1) >= config.MAX_PLAY_RATE:
            self.decimate += 1
        # ...and step up once more if we're still over the cap.
        while self.rate // self.decimate > config.MAX_PLAY_RATE:
            self.decimate += 1
        if self.decimate > 1:
            print("WAV %d Hz > cap %d: playing every %dth sample (re-encode to"
                  " 16k mono for best quality)"
                  % (self.rate, config.MAX_PLAY_RATE, self.decimate))

        # Bytes to advance per OUTPUT sample = one frame times the decimation.
        self._bstep = self._frame_size * self.decimate

        # Input buffer holds CHUNK_MS of *raw* frames; output holds the
        # decimated samples that actually reach the DACs.
        frames = (self.rate * config.CHUNK_MS) // 1000
        frames = max(frames, self._frame_size)
        self._in_buf = bytearray(frames * self._frame_size)
        self._out_buf = bytearray(frames // self.decimate + 1)
        # Reused memoryview so the steady-state read allocates nothing (a fresh
        # memoryview()[:n] every chunk was churning the heap and triggering GC
        # pauses mid-stream -> audible ticking).
        self._mv = memoryview(self._in_buf)
        # Run GC ourselves at a controlled point (once ~per second, in the gap
        # between chunks) so it never fires unpredictably during audio output.
        self._gc_every = max(1, 1000 // config.CHUNK_MS)
        self._since_gc = 0
        gc.collect()

        # Output-sample period (whole microseconds + a 0..255 fractional part in
        # 1/256 us units), computed from the *raw* rate scaled by decimation so
        # pitch stays exact. Small ints let _play_buf advance the clock with
        # time.ticks_add() and NEVER allocate mid-loop.
        num = 1_000_000 * self.decimate
        self._period_us = num // self.rate
        self._period_frac = ((num % self.rate) * 256) // self.rate

        self.level_peak = 0
        self.level_hf = 0
        self.playing = True
        self.paused = False
        self._played_frames = 0

    @property
    def position_s(self):
        return self._played_frames // self.rate if self.rate else 0

    def seek_seconds(self, delta):
        """Jump `delta` seconds within the current track (negative = back).
        Frame-aligned; clamps to the track bounds. Safe to call while playing."""
        if not self.playing or not self.rate:
            return
        target = self._played_frames + delta * self.rate
        n_frames = self._data_len // self._frame_size
        if target < 0:
            target = 0
        elif target > n_frames - 1:
            target = n_frames - 1
        self._file.seek(self._data_pos + target * self._frame_size)
        self._played_frames = target
        self._remaining = self._data_len - target * self._frame_size
        self.level_peak = 0
        self.level_hf = 0

    # ---- playback ----
    def step(self):
        """Play one chunk (~CHUNK_MS). Returns False when the track ends.
        Call repeatedly from the main loop; UI runs between calls."""
        if not self.playing or self.paused:
            return self.playing
        if self._remaining <= 0:
            self.stop()
            return False

        # Collect garbage here (chunk boundary, in the inter-chunk gap) instead
        # of letting it fire at a random moment during sample output.
        self._since_gc += 1
        if self._since_gc >= self._gc_every:
            self._since_gc = 0
            gc.collect()

        n = min(len(self._in_buf), self._remaining)
        n -= n % self._frame_size
        if n <= 0:
            self.stop()
            return False
        # Full chunk: read straight into the buffer (no allocation). Only the
        # short final chunk needs a sliced view.
        if n == len(self._in_buf):
            got = self._file.readinto(self._in_buf)
        else:
            got = self._file.readinto(self._mv[:n])
        if not got:
            self.stop()
            return False
        self._remaining -= got
        frames = got // self._frame_size          # raw frames read from file
        out_n = frames // self.decimate           # samples actually played
        if out_n <= 0:
            return True

        vol = (self.volume * self.volume * 256) // 10000  # perceptual-ish curve
        if self.bits == 16:
            _cvt16(self._in_buf, self._out_buf, out_n, self._bstep, vol)
        else:
            _cvt8(self._in_buf, self._out_buf, out_n, self._bstep, vol)

        # loudness for the visualizer (cheap, over the tiny output buffer)
        lvl = int(_meter(self._out_buf, out_n))
        self.level_peak = lvl >> 8
        self.level_hf = lvl & 0xFF

        self._play_buf(out_n)
        self._played_frames += frames             # position tracks file time
        return True

    @micropython.native
    def _play_buf(self, frames):
        out = self._out_buf
        wl = self._dac_l.write
        wr = self._dac_r.write
        period_us = self._period_us
        period_frac = self._period_frac
        ticks_us = time.ticks_us
        ticks_add = time.ticks_add
        ticks_diff = time.ticks_diff
        t = ticks_us()          # stays a small int -> no heap alloc in loop
        frac = 0
        for i in range(frames):
            v = out[i]
            wl(v)
            wr(v)
            t = ticks_add(t, period_us)
            frac += period_frac
            if frac >= 256:
                frac -= 256
                t = ticks_add(t, 1)
            while ticks_diff(t, ticks_us()) > 0:
                pass

    def pause(self):
        if self.playing:
            self.paused = True
            self._silence()

    def resume(self):
        self.paused = False

    def toggle_pause(self):
        if self.paused:
            self.resume()
        else:
            self.pause()

    def stop(self):
        self.playing = False
        self.paused = False
        self.level_peak = 0
        self.level_hf = 0
        if self._file:
            self._file.close()
            self._file = None
        self._silence()

    def vol_up(self):
        self.volume = min(100, self.volume + config.VOLUME_STEP)

    def vol_down(self):
        self.volume = max(0, self.volume - config.VOLUME_STEP)
