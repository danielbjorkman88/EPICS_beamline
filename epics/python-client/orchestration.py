from epics import PV
import threading
import time
import csv
from datetime import datetime


# =========================
# Motor PVs
# =========================

TARGET_PV = "BEAMLINE:MOTOR:TARGET"
POSITION_PV = "BEAMLINE:MOTOR:POSITION"
MOTOR_STATE_PV = "BEAMLINE:MOTOR:STATE"


# =========================
# Detector PVs
# =========================

DETECTOR_START_PV = "BEAMLINE:DETECTOR:START"
DETECTOR_STATE_PV = "BEAMLINE:DETECTOR:STATE"
DETECTOR_COUNTS_PV = "BEAMLINE:DETECTOR:COUNTS"


# =========================
# Create PV connections
# =========================

target = PV(TARGET_PV)
position = PV(POSITION_PV)
motor_state = PV(MOTOR_STATE_PV)

detector_start = PV(DETECTOR_START_PV)
detector_state = PV(DETECTOR_STATE_PV)
detector_counts = PV(DETECTOR_COUNTS_PV)


# =========================
# Motor callback handling
# =========================

motion_complete = threading.Event()

latest_motor_state = None


def motor_state_changed(pvname=None, value=None, **kwargs):
    """Called whenever the motor STATE PV changes."""

    global latest_motor_state

    latest_motor_state = value

    print(f"Motor state changed: {value}")

    if value in ("DONE", "ERROR"):
        motion_complete.set()


# =========================
# Detector callback handling
# =========================

acquisition_complete = threading.Event()

latest_detector_state = None


def detector_state_changed(pvname=None, value=None, **kwargs):
    """Called whenever the detector STATE PV changes."""

    global latest_detector_state

    latest_detector_state = value

    print(f"Detector state changed: {value}")

    if value in ("DONE", "ERROR"):
        acquisition_complete.set()


# =========================
# Connection setup
# =========================

def connect():
    """Connect to all required EPICS PVs."""

    pvs = (
        target,
        position,
        motor_state,
        detector_start,
        detector_state,
        detector_counts,
    )

    for pv in pvs:

        if not pv.wait_for_connection(timeout=5):
            raise RuntimeError(
                f"Could not connect to {pv.pvname}"
            )

    # Subscribe to asynchronous state changes
    motor_state.add_callback(motor_state_changed)
    detector_state.add_callback(detector_state_changed)


# =========================
# Motor control
# =========================

def move_motor(target_position, timeout=30):
    """
    Command the motor to a target position and wait
    for the movement to complete.
    """

    print(
        f"\nMoving motor to "
        f"{target_position:.1f} mm"
    )

    current_position = position.get()

    # Already at target
    if abs(current_position - target_position) < 0.01:

        print("Motor is already at target position.")

        return current_position

    # Clear previous completion event
    motion_complete.clear()

    # Send movement command
    target.put(target_position)

    # Wait for motor callback
    finished = motion_complete.wait(timeout=timeout)

    if not finished:
        raise TimeoutError(
            "Motor motion timed out"
        )

    if latest_motor_state == "ERROR":
        raise RuntimeError(
            "Motor reported ERROR"
        )

    # Read final position
    final_position = position.get()

    # Verify readback
    if abs(final_position - target_position) > 0.01:

        raise RuntimeError(
            f"Motor reported DONE but position is "
            f"{final_position:.1f} mm instead of "
            f"{target_position:.1f} mm"
        )

    print(
        f"Motor reached "
        f"{final_position:.1f} mm"
    )

    return final_position


def generate_scan_positions(start, stop, step):
    """Generate motor positions for a scan."""

    if step <= 0:
        raise ValueError("Step must be positive.")

    if stop < start:
        raise ValueError("Stop must be greater than or equal to start.")

    positions = []

    current = start

    while current <= stop:
        positions.append(current)
        current += step

    return positions


# =========================
# Detector acquisition
# =========================

def acquire_detector(timeout=10):
    """
    Start a detector acquisition and wait
    for it to complete.
    """

    print("\nStarting detector acquisition")

    # Clear previous completion event
    acquisition_complete.clear()

    # Start acquisition
    detector_start.put(1)

    # Wait for detector callback
    finished = acquisition_complete.wait(
        timeout=timeout
    )

    if not finished:
        raise TimeoutError(
            "Detector acquisition timed out"
        )

    if latest_detector_state == "ERROR":
        raise RuntimeError(
            "Detector reported ERROR"
        )

    # Read measured counts
    measured_counts = detector_counts.get()

    print(
        f"Detector measurement: "
        f"{measured_counts:.0f} counts"
    )

    return measured_counts


# =========================
# Main experiment
# =========================

if __name__ == "__main__":

    connect()

    scan_positions = generate_scan_positions(
    start=0,
    stop=25,
    step=5,)

    results = []

    print("\nStarting scan")
    print("====================")

    for index, scan_position in enumerate(scan_positions, start=1):

        print(
            f"\nScan point {index}/{len(scan_positions)}"
        )
        print(
            f"Position: {scan_position:.1f} mm"
        )



        # Move motor
        actual_position = move_motor(
            scan_position
        )

        # Acquire detector measurement
        measured_counts = acquire_detector()

        # Store result
        result = {
            "position": actual_position,
            "counts": measured_counts,
	    "timestamp": datetime.now().isoformat(),
        }

        results.append(result)

        print(
            f"Recorded: "
            f"{actual_position:.1f} mm → "
            f"{measured_counts:.1f} counts"
        )

    with open("scan_results.csv", "w", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=["position", "counts", "timestamp"]
        )

        writer.writeheader()
        writer.writerows(results)

    print("\nSaved scan results to scan_results.csv")



    print("\n====================")
    print("Scan complete")
    print("====================")

    print("\nResults:")

    for result in results:

        print(
            f"{result['position']:6.1f} mm"
            f"   {result['counts']:8.1f} counts"
        )