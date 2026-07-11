# Buttons + rotary encoder, interrupt-driven with debouncing.
# Events are queued as small ints; main loop drains them with get_event().
import time
from machine import Pin

import config

# Event codes
EV_UP = 1
EV_DOWN = 2
EV_SELECT = 3
EV_BACK = 4       # encoder push
EV_VOL_UP = 5
EV_VOL_DOWN = 6

# Quadrature decode table: index = (prev_state << 2) | state, value = -1/0/+1
_ENC_TABLE = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class Inputs:
    def __init__(self):
        self._queue = []
        self._last_press = {}

        # GPIO34 is input-only and has no internal pull; the board provides
        # an external 10k pullup (R6). 32/33/27 use internal pullups.
        self._btn_up = Pin(config.PIN_BTN_UP, Pin.IN, Pin.PULL_UP)
        self._btn_sel = Pin(config.PIN_BTN_SELECT, Pin.IN, Pin.PULL_UP)
        self._btn_down = Pin(config.PIN_BTN_DOWN, Pin.IN)
        self._enc_sw = Pin(config.PIN_ENC_SW, Pin.IN, Pin.PULL_UP)

        self._enc_a = Pin(config.PIN_ENC_A, Pin.IN, Pin.PULL_UP)
        self._enc_b = Pin(config.PIN_ENC_B, Pin.IN, Pin.PULL_UP)
        self._enc_state = (self._enc_a.value() << 1) | self._enc_b.value()
        self._enc_accum = 0

        self._btn_up.irq(self._make_btn_irq(EV_UP), Pin.IRQ_FALLING)
        self._btn_sel.irq(self._make_btn_irq(EV_SELECT), Pin.IRQ_FALLING)
        self._btn_down.irq(self._make_btn_irq(EV_DOWN), Pin.IRQ_FALLING)
        self._enc_sw.irq(self._make_btn_irq(EV_BACK), Pin.IRQ_FALLING)
        self._enc_a.irq(self._enc_irq, Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self._enc_b.irq(self._enc_irq, Pin.IRQ_FALLING | Pin.IRQ_RISING)

    def _make_btn_irq(self, event):
        def handler(pin):
            now = time.ticks_ms()
            last = self._last_press.get(event, 0)
            if time.ticks_diff(now, last) > config.DEBOUNCE_MS:
                self._last_press[event] = now
                if len(self._queue) < 16:
                    self._queue.append(event)
        return handler

    def _enc_irq(self, pin):
        state = (self._enc_a.value() << 1) | self._enc_b.value()
        step = _ENC_TABLE[(self._enc_state << 2) | state]
        self._enc_state = state
        self._enc_accum += step
        # EC11 gives 4 quadrature transitions per detent.
        # Direction is intentionally reversed here (CW = volume down) to match
        # the knob's physical orientation on the board.
        if self._enc_accum >= 4:
            self._enc_accum = 0
            if len(self._queue) < 16:
                self._queue.append(EV_VOL_DOWN)
        elif self._enc_accum <= -4:
            self._enc_accum = 0
            if len(self._queue) < 16:
                self._queue.append(EV_VOL_UP)

    def get_event(self):
        """Return next queued event code, or None."""
        if self._queue:
            return self._queue.pop(0)
        return None

    # Live button levels (active-low: pressed reads 0). Used by the main loop
    # for press-and-hold behaviour like scrubbing, which edge events can't give.
    def up_held(self):
        return self._btn_up.value() == 0

    def down_held(self):
        return self._btn_down.value() == 0

    def clear(self):
        self._queue.clear()
