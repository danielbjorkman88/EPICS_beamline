import sys

from epics import PV

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from PySide6.QtCore import (
    QTimer,
    Qt,
)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
)

import pyvista as pv
from pyvistaqt import QtInteractor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# =========================
# EPICS PVs
# =========================

motor_position = PV(
    "BEAMLINE:MOTOR:POSITION"
)

motor_state = PV(
    "BEAMLINE:MOTOR:STATE"
)

motor_target = PV(
    "BEAMLINE:MOTOR:TARGET"
)

detector_state = PV(
    "BEAMLINE:DETECTOR:STATE"
)

detector_counts = PV(
    "BEAMLINE:DETECTOR:COUNTS"
)

detector_start = PV(
    "BEAMLINE:DETECTOR:START"
)


# =========================
# GUI
# =========================

class BeamlineGUI(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("Beamline Control")

        self.resize(700, 650)

        # Store measurements
        self.positions = []
        self.counts = []

        self.last_detector_state = None


        # =========================
        # Main layout
        # =========================

        layout = QVBoxLayout()


        # =========================
        # Motor information
        # =========================

        self.position_label = QLabel(
            "Motor position: -- mm"
        )

        self.motor_state_label = QLabel(
            "Motor state: --"
        )

        layout.addWidget(
            self.position_label
        )

        layout.addWidget(
            self.motor_state_label
        )


        # =========================
        # Motor control
        # =========================

        motor_layout = QHBoxLayout()

        self.target_input = QLineEdit()

        self.target_input.setPlaceholderText(
            "Target position (mm)"
        )

        move_button = QPushButton(
            "Move"
        )

        move_button.clicked.connect(
            self.move_motor
        )

        motor_layout.addWidget(
            self.target_input
        )

        motor_layout.addWidget(
            move_button
        )

        layout.addLayout(
            motor_layout
        )


        # =========================
        # Detector information
        # =========================

        self.detector_state_label = QLabel(
            "Detector state: --"
        )

        self.counts_label = QLabel(
            "Detector counts: --"
        )

        acquire_button = QPushButton(
            "Acquire"
        )

        acquire_button.clicked.connect(
            self.acquire_detector
        )

        layout.addWidget(
            self.detector_state_label
        )

        layout.addWidget(
            self.counts_label
        )

        layout.addWidget(
            acquire_button
        )


        # =========================
        # Plot
        # =========================

        self.figure = Figure()

        self.canvas = FigureCanvasQTAgg(
            self.figure
        )

        self.ax = self.figure.add_subplot(111)

        self.ax.set_xlabel(
            "Motor position (mm)"
        )

        self.ax.set_ylabel(
            "Detector counts"
        )

        self.ax.set_title(
            "Beamline scan"
        )

        self.ax.grid(True)

        layout.addWidget(
            self.canvas
        )


        self.setLayout(layout)


        # =========================
        # Periodic EPICS update
        # =========================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_from_epics
        )

        self.timer.start(100)


        # Initial values

        self.update_from_epics()


    # =========================
    # Motor control
    # =========================

    def move_motor(self):

        try:

            target = float(
                self.target_input.text()
            )

            motor_target.put(target)

        except ValueError:

            self.motor_state_label.setText(
                "Invalid target position"
            )


    # =========================
    # Detector control
    # =========================

    def acquire_detector(self):

        detector_start.put(1)


    # =========================
    # EPICS monitoring
    # =========================

    def update_from_epics(self):

        position = motor_position.get()
        motor_status = motor_state.get()
        detector_status = detector_state.get()
        counts = detector_counts.get()


        # Update motor display

        if position is not None:

            self.position_label.setText(
                f"Motor position: "
                f"{position:.1f} mm"
            )


        if motor_status is not None:

            self.motor_state_label.setText(
                f"Motor state: "
                f"{motor_status}"
            )


        # Update detector display

        if detector_status is not None:

            self.detector_state_label.setText(
                f"Detector state: "
                f"{detector_status}"
            )


        if counts is not None:

            self.counts_label.setText(
                f"Detector counts: "
                f"{counts:.1f}"
            )


        # =========================
        # Record completed acquisition
        # =========================

        if (
            detector_status == "DONE"
            and self.last_detector_state != "DONE"
        ):

            if (
                position is not None
                and counts is not None
            ):

                self.positions.append(
                    float(position)
                )

                self.counts.append(
                    float(counts)
                )

                self.update_plot()


        self.last_detector_state = detector_status


    # =========================
    # Plot
    # =========================

    def update_plot(self):

        self.ax.clear()

        self.ax.plot(
            self.positions,
            self.counts,
            marker="o",
        )

        self.ax.set_xlabel(
            "Motor position (mm)"
        )

        self.ax.set_ylabel(
            "Detector counts"
        )

        self.ax.set_title(
            "Beamline scan"
        )

        self.ax.grid(True)

        self.figure.tight_layout()

        self.canvas.draw()


# =========================
# Start application
# =========================

app = QApplication(sys.argv)

window = BeamlineGUI()

window.show()

sys.exit(app.exec())