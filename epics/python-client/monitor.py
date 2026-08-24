from epics import PV
import time


def temperature_changed(pvname=None, value=None, **kwargs):
    print(f"{pvname}: {value:.2f} °C")


temperature = PV("BEAMLINE:TEMP")

if not temperature.wait_for_connection(timeout=5):
    raise RuntimeError("Could not connect to BEAMLINE:TEMP")

temperature.add_callback(temperature_changed)

print("Monitoring temperature...")
print("Press Ctrl+C to stop.")

while True:
    time.sleep(0.2)