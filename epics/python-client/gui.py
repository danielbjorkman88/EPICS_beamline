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
import numpy as np

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
        # Plots
        # =========================

        plot_splitter = QSplitter(
            Qt.Horizontal
        )


        # =========================
        # 2D Matplotlib plot
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

        plot_splitter.addWidget(
            self.canvas
        )


        # =========================
        # 3D PyVista plot
        # =========================

        self.plotter = QtInteractor(
            self
        )

        self.plotter.set_background(
            "white"
        )

        plot_splitter.addWidget(
            self.plotter
        )


        # Give the two plots equal space

        plot_splitter.setSizes(
            [300, 300]
        )

        layout.addWidget(
            plot_splitter
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
    # 3D Plot
    # =========================

    def update_3d_plot(self):

        # Clear previous scene
        self.plotter.clear()

        # Black background
        self.plotter.set_background("black")


        # =================================================
        # Parameters
        # =================================================

        beam_length = 50
        quadrupole_x = 15
        quadrupole_length = 10

        pipe_radius = 12

        # Quadrupole field gradient
        # Arbitrary units for visualization
        gradient = 1.0


        # =================================================
        # Beam pipe
        # =================================================

        pipe = pv.Cylinder(
            center=(12.5, 0, 0),
            direction=(1, 0, 0),
            radius=pipe_radius,
            height=beam_length,
            resolution=64,
        )

        self.plotter.add_mesh(
            pipe,
            color="lightgray",
            opacity=0.15,
            smooth_shading=True,
        )


        # =================================================
        # Quadrupole poles
        # =================================================

        pole_radius = 4
        pole_distance = 6

        pole_positions = [
            (quadrupole_x,  pole_distance, 0),
            (quadrupole_x, -pole_distance, 0),
            (quadrupole_x, 0,  pole_distance),
            (quadrupole_x, 0, -pole_distance),
        ]

        for center in pole_positions:

            pole = pv.Cylinder(
                center=center,
                direction=(1, 0, 0),
                radius=pole_radius,
                height=quadrupole_length,
                resolution=32,
            )

            self.plotter.add_mesh(
                pole,
                color="gray",
                opacity=0.65,
                smooth_shading=True,
            )


        # =================================================
        # Quadrupole magnetic field
        # =================================================

        # Field grid in the transverse Y-Z plane.
        #
        # Beam direction = X
        #
        # B_y = G * Z
        # B_z = G * Y

        # Dense transverse grid
        y_values = np.linspace(
            -5,
            5,
            11,
        )

        z_values = np.linspace(
            -5,
            5,
            11,
        )


        # Several slices along the magnet
        x_values = np.linspace(
            quadrupole_x - 4,
            quadrupole_x + 4,
            7,
        )

        points = []
        vectors = []
        magnitudes = []

        for x in x_values:

            for y in y_values:

                for z in z_values:

                    # Ideal quadrupole field
                    By = gradient * z
                    Bz = gradient * y

                    Bx = 0.0

                    magnitude = (
                        By**2 +
                        Bz**2
                    ) ** 0.5

                    points.append(
                        [x, y, z]
                    )

                    vectors.append(
                        [Bx, By, Bz]
                    )

                    magnitudes.append(
                        magnitude
                    )


        # Create point cloud
        field = pv.PolyData(points)

        field["B"] = vectors
        field["B_mag"] = magnitudes


        # =================================================
        # Create arrows
        # =================================================

        arrows = field.glyph(
            orient="B",
            scale="B",
            factor=0.8,
        )


        # Colour arrows according to field magnitude
        self.plotter.add_mesh(
            arrows,
            scalars="B_mag",
            cmap="plasma",
            show_scalar_bar=True,
            scalar_bar_args={
                "title": "|B|  (arb. units)",
                "color": "white",
            },
        )


        # =================================================
        # Beam axis
        # =================================================

        beam = pv.Line(
            pointa=(-10, 0, 0),
            pointb=(40, 0, 0),
        )

        self.plotter.add_mesh(
            beam,
            color="yellow",
            line_width=3,
        )


        # =================================================
        # Measured scan points
        # =================================================

        if self.positions:

            points = []

            for position, counts in zip(
                self.positions,
                self.counts,
            ):

                # Scale detector counts for visualization
                z = counts / 100

                points.append(
                    [
                        position,
                        0,
                        z,
                    ]
                )


            mesh = pv.PolyData(points)

            self.plotter.add_mesh(
                mesh,
                color="red",
                point_size=15,
                render_points_as_spheres=True,
            )


            # Connect measurements

            if len(points) > 1:

                line = pv.lines_from_points(
                    points
                )

                self.plotter.add_mesh(
                    line,
                    color="red",
                    line_width=3,
                )


        # =================================================
        # Axes
        # =================================================

        self.plotter.show_bounds(
            grid="front",
            location="outer",
            xtitle="Beam direction (mm)",
            ytitle="Transverse Y (mm)",
            ztitle="Transverse Z / signal",
            color="white",
        )

        self.plotter.add_axes(
            line_width=2,
            color="white",
        )


        # =================================================
        # Camera
        # =================================================

        self.plotter.reset_camera()

        self.plotter.render()

    
    
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

        self.figure.tight_layout()

        self.canvas.draw()

        self.update_3d_plot()


# =========================
# Start application
# =========================

app = QApplication(sys.argv)

window = BeamlineGUI()

window.show()

sys.exit(app.exec())