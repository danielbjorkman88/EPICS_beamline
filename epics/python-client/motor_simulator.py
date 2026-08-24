from epics import PV
import time
import threading


TARGET_PV = "BEAMLINE:MOTOR:TARGET"
POSITION_PV = "BEAMLINE:MOTOR:POSITION"
STATE_PV = "BEAMLINE:MOTOR:STATE"

target = PV(TARGET_PV)
position = PV(POSITION_PV)
state = PV(STATE_PV)


def move_motor(new_target):
    """Simulate a motor moving towards a target position."""

    current = position.get()

    print(f"Moving from {current:.1f} mm to {new_target:.1f} mm")

    state.put("MOVING")

    while abs(current - new_target) > 0.01:

        step = 1.0 if new_target > current else -1.0
        current += step

        # Don't overshoot the target
        if (step > 0 and current > new_target) or (
            step < 0 and current < new_target
        ):
            current = new_target

        position.put(current)

        print(f"Position: {current:.1f} mm")

        time.sleep(0.5)

    position.put(new_target)
    state.put("DONE")

    print(f"Motion complete: {new_target:.1f} mm")


def target_changed(pvname=None, value=None, **kwargs):
    """Called whenever the target PV changes."""

    new_target = float(value)

    # Run the motor movement in a separate thread
    thread = threading.Thread(
        target=move_motor,
        args=(new_target,),
        daemon=True,
    )

    thread.start()


if not target.wait_for_connection(timeout=5):
    raise RuntimeError(f"Could not connect to {TARGET_PV}")

if not position.wait_for_connection(timeout=5):
    raise RuntimeError(f"Could not connect to {POSITION_PV}")

if not state.wait_for_connection(timeout=5):
    raise RuntimeError(f"Could not connect to {STATE_PV}")


target.add_callback(target_changed)

print("Motor simulator running.")
print(f"Watching {TARGET_PV}")
print("Press Ctrl+C to stop.")

while True:
    time.sleep(0.2)