import csv
import matplotlib.pyplot as plt


positions = []
counts = []


with open("scan_results.csv", "r") as file:

    reader = csv.DictReader(file)

    for row in reader:
        positions.append(float(row["position"]))
        counts.append(float(row["counts"]))


plt.plot(
    positions,
    counts,
    marker="o"
)

plt.xlabel("Motor position (mm)")
plt.ylabel("Detector counts")
plt.title("Beamline scan")

plt.grid(True)

plt.tight_layout()

plt.show()