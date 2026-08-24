from epics import PV

temperature = PV("BEAMLINE:TEMP")

if not temperature.wait_for_connection(timeout=5):
    raise RuntimeError("Could not connect to BEAMLINE:TEMP")

print("Connected:", temperature.connected)
print("Initial temperature:", temperature.get())

temperature.put(21.5)

print("New temperature:", temperature.get())