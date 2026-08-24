from epics import PV
import time
import threading
import math
import random


START_PV = "BEAMLINE:DETECTOR:START"
STATE_PV = "BEAMLINE:DETECTOR:STATE"
COUNTS_PV = "BEAMLINE:DETECTOR:COUNTS"

MOTOR_POSITION_PV = "BEAMLINE:MOTOR:POSITION"


start = PV(START_PV)
state = PV(STATE_PV)
counts = PV(COUNTS_PV)

motor_position = PV(MOTOR_POSITION_PV)


def acquire():
    """Simulate a detector acquisition."""

    state.put("ACQUIRING")

    position = motor_position.get()

    print(
        f"Acquiring measurement at "
        f"{position:.1f} mm"
    )

    # Simulate detector exposure time
    time.sleep(2)

    # Simulate a measurement with a peak around 15 mm
    signal = 2500 * math.exp(
        -((position - 15) ** 2) / (2 * 5 ** 2)
    )

    # Add some measurement noise
    noise = random.uniform(-50, 50)

    measured_counts = max(0, signal + noise)

    counts.put(measured_counts)

    state.put("DONE")

    print(
        f"Measurement complete: "
        f"{measured_counts:.0f} counts"
    )


def start_changed(pvname=None, value=None, **kwargs):
    """Called whenever the detector START PV changes."""

    if value != 1:
        return

    # Reset START so another acquisition can be triggered
    start.put(0)

    # Run acquisition asynchronously
    thread = threading.Thread(
        target=acquire,
        daemon=True,
    )

    thread.start()


# Connect to all PVs
for pv in (start, state, counts, motor_position):

    if not pv.wait_for_connection(timeout=5):
        raise RuntimeError(
            f"Could not connect to {pv.pvname}"
        )


# Listen for acquisition commands
start.add_callback(start_changed)


print("Detector simulator running.")
print(f"Watching {START_PV}")
print(f"Reading motor position from {MOTOR_POSITION_PV}")
print("Press Ctrl+C to stop.")


while True:
    time.sleep(0.2)