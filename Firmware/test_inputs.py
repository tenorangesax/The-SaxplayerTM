# test_inputs.py -- standalone input test, bypasses display/SD entirely.
# Tests SW1/SW2/SW3, encoder turn, and encoder push.
#
# Run:  mpremote connect /dev/cu.usbserial-XXXX run test_inputs.py
#
# Shows two kinds of output:
#   - "EVENT: ..."  a debounced/decoded event actually reached the queue
#   - "raw ..."     live pin levels, printed whenever any of them change
#
# The raw line matters most for the encoder right now: if A/B/ENC_SW
# never change at all while you turn/press it, that's the C4/C5-blocks-DC
# hardware bug -- the common pin never actually reaches 0V, so the pins
# can't be pulled low no matter what the firmware does.

import time
import inputs

i = inputs.Inputs()

EVENT_NAMES = {
    1: "UP (SW1)",
    2: "DOWN (SW3)",
    3: "SELECT (SW2)",
    4: "ENCODER PUSH",
    5: "VOL UP (encoder CW)",
    6: "VOL DOWN (encoder CCW)",
}

print("Testing SW1/SW2/SW3 + rotary encoder (turn and push).")
print("Press buttons / turn the knob now. Ctrl-C to stop.\n")

last_raw = None
try:
    while True:
        ev = i.get_event()
        if ev is not None:
            print("EVENT:", EVENT_NAMES.get(ev, ev))

        raw = (
            i._btn_up.value(),
            i._btn_sel.value(),
            i._btn_down.value(),
            i._enc_sw.value(),
            i._enc_a.value(),
            i._enc_b.value(),
        )
        if raw != last_raw:
            print("raw  SW1=%d SW2=%d SW3=%d  ENC_SW=%d ENC_A=%d ENC_B=%d" % raw)
            last_raw = raw

        time.sleep_ms(20)
except KeyboardInterrupt:
    print("stopped")
