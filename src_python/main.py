#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ambre chamber
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/project-Ambre-chamber"
__date__ = "31-08-2020"
__version__ = "2.0"
# pylint: disable=bare-except, broad-except, try-except-raise

import os
import sys
import time

import numpy as np
import psutil

from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as QtWid
from PyQt5.QtCore import QDateTime
import pyqtgraph as pg

from dvg_debug_functions import tprint, dprint, print_fancy_traceback as pft
from dvg_pyqt_controls import (
    create_LED_indicator,
    create_Toggle_button,
    SS_TEXTBOX_READ_ONLY,
    SS_GROUP,
)
from dvg_pyqt_filelogger import FileLogger
from dvg_pyqtgraph_threadsafe import (
    HistoryChartCurve,
    LegendSelect,
    PlotManager,
)

from dvg_devices.Arduino_protocol_serial import Arduino
from dvg_qdeviceio import QDeviceIO


TRY_USING_OPENGL = True
if TRY_USING_OPENGL:
    try:
        import OpenGL.GL as gl  # pylint: disable=unused-import
    except:
        print("OpenGL acceleration: Disabled")
        print("To install: `conda install pyopengl` or `pip install pyopengl`")
    else:
        print("OpenGL acceleration: Enabled")
        pg.setConfigOptions(useOpenGL=True)
        pg.setConfigOptions(antialias=True)
        pg.setConfigOptions(enableExperimental=True)

# Global pyqtgraph configuration
# pg.setConfigOptions(leftButtonPan=False)
pg.setConfigOption("foreground", "#EEE")

# Constants
# fmt: off
DAQ_INTERVAL_MS    = 1000  # [ms]
CHART_INTERVAL_MS  = 500   # [ms]
CHART_HISTORY_TIME = 3600  # [s]
# fmt: on

# Show debug info in terminal? Warning: Slow! Do not leave on unintentionally.
DEBUG = False


def get_current_date_time():
    cur_date_time = QDateTime.currentDateTime()
    return (
        cur_date_time.toString("dd-MM-yyyy"),  # Date
        cur_date_time.toString("HH:mm:ss"),  # Time
        cur_date_time.toString("yyMMdd_HHmmss"),  # Reverse notation date-time
    )


# ------------------------------------------------------------------------------
#   Arduino state
# ------------------------------------------------------------------------------


class State(object):
    """Reflects the actual readings, parsed into separate variables, of the
    Arduino. There should only be one instance of the State class.
    """

    def __init__(self):
        self.time = np.nan  # [s]
        self.ds18b20_temp = np.nan  # ['C]
        self.dht22_temp = np.nan  # ['C]
        self.dht22_humi = np.nan  # [%]
        self.is_valve_open = False

        # Automatic valve control
        self.humi_threshold = np.nan  # [%]
        self.open_valve_when_super_humi = np.nan


state = State()

# ------------------------------------------------------------------------------
#   MainWindow
# ------------------------------------------------------------------------------


class MainWindow(QtWid.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.setWindowTitle("Ambre chamber")
        self.setGeometry(350, 50, 960, 800)
        self.setStyleSheet(SS_TEXTBOX_READ_ONLY + SS_GROUP)

        # -------------------------
        #   Top frame
        # -------------------------

        # Left box
        self.qlbl_update_counter = QtWid.QLabel("0")
        self.qlbl_DAQ_rate = QtWid.QLabel("DAQ: nan Hz")
        self.qlbl_DAQ_rate.setStyleSheet("QLabel {min-width: 7em}")

        vbox_left = QtWid.QVBoxLayout()
        vbox_left.addWidget(self.qlbl_update_counter, stretch=0)
        vbox_left.addStretch(1)
        vbox_left.addWidget(self.qlbl_DAQ_rate, stretch=0)

        # Middle box
        self.qlbl_title = QtWid.QLabel(
            "Ambre chamber",
            font=QtGui.QFont("Palatino", 14, weight=QtGui.QFont.Bold),
        )
        self.qlbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.qlbl_cur_date_time = QtWid.QLabel("00-00-0000    00:00:00")
        self.qlbl_cur_date_time.setAlignment(QtCore.Qt.AlignCenter)
        self.qpbt_record = create_Toggle_button(
            "Click to start recording to file", minimumWidth=300
        )
        # fmt: off
        self.qpbt_record.clicked.connect(lambda state: log.record(state)) # pylint: disable=unnecessary-lambda
        # fmt: on

        vbox_middle = QtWid.QVBoxLayout()
        vbox_middle.addWidget(self.qlbl_title)
        vbox_middle.addWidget(self.qlbl_cur_date_time)
        vbox_middle.addWidget(self.qpbt_record)

        # Right box
        self.qpbt_exit = QtWid.QPushButton("Exit")
        self.qpbt_exit.clicked.connect(self.close)
        self.qpbt_exit.setMinimumHeight(30)
        self.qlbl_recording_time = QtWid.QLabel(alignment=QtCore.Qt.AlignRight)

        vbox_right = QtWid.QVBoxLayout()
        vbox_right.addWidget(self.qpbt_exit, stretch=0)
        vbox_right.addStretch(1)
        vbox_right.addWidget(self.qlbl_recording_time, stretch=0)

        # Round up top frame
        hbox_top = QtWid.QHBoxLayout()
        hbox_top.addLayout(vbox_left, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_middle, stretch=0)
        hbox_top.addStretch(1)
        hbox_top.addLayout(vbox_right, stretch=0)

        # -------------------------
        #   Bottom frame
        # -------------------------

        #  Charts
        # -------------------------

        self.gw = pg.GraphicsLayoutWidget()

        # Plot: Temperature: DS18B20
        p = {"color": "#EEE", "font-size": "10pt"}
        self.pi_ds18b20_temp = self.gw.addPlot(row=0, col=0)
        self.pi_ds18b20_temp.setLabel("left", text="temperature (°C)", **p)

        # Plot: Temperature: DHT 22
        self.pi_dht22_temp = self.gw.addPlot(row=1, col=0)
        self.pi_dht22_temp.setLabel("left", text="temperature (°C)", **p)

        # Plot: Humidity: DHT22
        self.pi_dht22_humi = self.gw.addPlot(row=2, col=0)
        self.pi_dht22_humi.setLabel("left", text="humidity (%)", **p)

        self.plots = [
            self.pi_ds18b20_temp,
            self.pi_dht22_humi,
            self.pi_dht22_temp,
        ]
        for plot in self.plots:
            plot.setClipToView(True)
            plot.showGrid(x=1, y=1)
            plot.setLabel("bottom", text="history (s)", **p)
            plot.setMenuEnabled(True)
            plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
            plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
            plot.setAutoVisible(y=True)
            plot.setRange(xRange=[-CHART_HISTORY_TIME, 0])

        # Curves
        capacity = round(CHART_HISTORY_TIME * 1e3 / DAQ_INTERVAL_MS)
        PEN_01 = pg.mkPen(color=[255, 255, 0], width=3)
        PEN_02 = pg.mkPen(color=[0, 255, 255], width=3)

        self.tscurve_ds18b20_temp = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_ds18b20_temp.plot(
                pen=PEN_01, name="DS18B20 temp."
            ),
        )
        self.tscurve_dht22_temp = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_dht22_temp.plot(
                pen=PEN_01, name="DHT22 temp."
            ),
        )
        self.tscurve_dht22_humi = HistoryChartCurve(
            capacity=capacity,
            linked_curve=self.pi_dht22_humi.plot(
                pen=PEN_02, name="DHT22 humi."
            ),
        )
        self.tscurves = [
            self.tscurve_ds18b20_temp,
            self.tscurve_dht22_temp,
            self.tscurve_dht22_humi,
        ]

        #  Group `Readings`
        # -------------------------

        legend = LegendSelect(
            linked_curves=self.tscurves, hide_toggle_button=True
        )

        p = {
            "readOnly": True,
            "alignment": QtCore.Qt.AlignRight,
            "maximumWidth": 54,
        }
        self.qlin_ds18b20_temp = QtWid.QLineEdit(**p)
        self.qlin_dht22_temp = QtWid.QLineEdit(**p)
        self.qlin_dht22_humi = QtWid.QLineEdit(**p)

        # fmt: off
        legend.grid.setHorizontalSpacing(6)
        legend.grid.addWidget(self.qlin_ds18b20_temp  , 0, 2)
        legend.grid.addWidget(QtWid.QLabel("± 0.5 °C"), 0, 3)
        legend.grid.addWidget(self.qlin_dht22_temp    , 1, 2)
        legend.grid.addWidget(QtWid.QLabel("± 0.5 °C"), 1, 3)
        legend.grid.addWidget(self.qlin_dht22_humi    , 2, 2)
        legend.grid.addWidget(QtWid.QLabel("± 3 %")   , 2, 3)
        # fmt: on

        qgrp_readings = QtWid.QGroupBox("Readings")
        qgrp_readings.setLayout(legend.grid)

        #  Group 'Log comments'
        # -------------------------

        self.qtxt_comments = QtWid.QTextEdit()
        grid = QtWid.QGridLayout()
        grid.addWidget(self.qtxt_comments, 0, 0)

        qgrp_comments = QtWid.QGroupBox("Log comments")
        qgrp_comments.setLayout(grid)

        #  Group 'Charts'
        # -------------------------

        self.plot_manager = PlotManager(parent=self)
        self.plot_manager.add_autorange_buttons(linked_plots=self.plots)
        self.plot_manager.add_preset_buttons(
            linked_plots=self.plots,
            linked_curves=self.tscurves,
            presets=[
                {
                    "button_label": "00:30",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-30, 0),
                },
                {
                    "button_label": "01:00",
                    "x_axis_label": "history (sec)",
                    "x_axis_divisor": 1,
                    "x_axis_range": (-60, 0),
                },
                {
                    "button_label": "10:00",
                    "x_axis_label": "history (min)",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-10, 0),
                },
                {
                    "button_label": "30:00",
                    "x_axis_label": "history (min)",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-30, 0),
                },
                {
                    "button_label": "60:00",
                    "x_axis_label": "history (min)",
                    "x_axis_divisor": 60,
                    "x_axis_range": (-60, 0),
                },
            ],
        )
        self.plot_manager.add_clear_button(linked_curves=self.tscurves)
        self.plot_manager.perform_preset(1)

        qgrp_chart = QtWid.QGroupBox("Charts")
        qgrp_chart.setLayout(self.plot_manager.grid)

        #  Group 'Valve control'
        # -------------------------

        self.LED_is_valve_open = create_LED_indicator()
        self.qlin_humi_threshold = QtWid.QLineEdit(
            "%d" % state.humi_threshold,
            alignment=QtCore.Qt.AlignRight,
            maximumWidth=36,
        )
        self.qlin_humi_threshold.editingFinished.connect(
            self.process_qlin_humi_threshold
        )
        self.qpbt_open_when_super_humi = QtWid.QPushButton(
            (
                "humidity > threshold"
                if state.open_valve_when_super_humi
                else "humidity < threshold"
            ),
            checkable=True,
            checked=state.open_valve_when_super_humi,
        )
        self.qpbt_open_when_super_humi.clicked.connect(
            self.process_qpbt_open_when_super_humi
        )

        # fmt: off
        grid = QtWid.QGridLayout()
        grid.addWidget(QtWid.QLabel("Is valve open?")    , 0, 0)
        grid.addWidget(self.LED_is_valve_open            , 0, 1)
        grid.addWidget(QtWid.QLabel("Humidity threshold"), 1, 0)
        grid.addWidget(self.qlin_humi_threshold          , 1, 1)
        grid.addWidget(QtWid.QLabel("%")                 , 1, 2)
        grid.addWidget(QtWid.QLabel("Open valve when")   , 2, 0)
        grid.addWidget(self.qpbt_open_when_super_humi    , 2, 1, 1, 2)
        grid.setAlignment(QtCore.Qt.AlignTop)
        # fmt: on

        qgrp_valve = QtWid.QGroupBox("Valve control")
        qgrp_valve.setLayout(grid)

        # Round up right frame
        vbox = QtWid.QVBoxLayout()
        vbox.addWidget(qgrp_readings)
        vbox.addWidget(qgrp_comments)
        vbox.addWidget(qgrp_valve)  # , alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(qgrp_chart, alignment=QtCore.Qt.AlignLeft)
        vbox.addStretch()

        # Round up bottom frame
        hbox_bot = QtWid.QHBoxLayout()
        hbox_bot.addWidget(self.gw, 1)
        hbox_bot.addLayout(vbox, 0)

        # -------------------------
        #   Round up full window
        # -------------------------

        vbox = QtWid.QVBoxLayout(self)
        vbox.addLayout(hbox_top, stretch=0)
        vbox.addSpacerItem(QtWid.QSpacerItem(0, 10))
        vbox.addLayout(hbox_bot, stretch=1)

    # --------------------------------------------------------------------------
    #   Handle controls
    # --------------------------------------------------------------------------

    @QtCore.pyqtSlot()
    def process_qlin_humi_threshold(self):
        try:
            humi_threshold = float(self.qlin_humi_threshold.text())
        except (TypeError, ValueError):
            humi_threshold = 50
        except:
            raise

        state.humi_threshold = np.clip(humi_threshold, 0, 100)
        self.qlin_humi_threshold.setText("%.0f" % state.humi_threshold)
        qdev_ard.send(ard.write, "th%.0f" % state.humi_threshold)

    @QtCore.pyqtSlot()
    def process_qpbt_open_when_super_humi(self):
        if self.qpbt_open_when_super_humi.isChecked():
            state.open_valve_when_super_humi = True
            self.qpbt_open_when_super_humi.setText("humidity > threshold")
            qdev_ard.send(ard.write, "open when super humi")

        else:
            state.open_valve_when_super_humi = False
            self.qpbt_open_when_super_humi.setText("humidity < threshold")
            qdev_ard.send(ard.write, "open when sub humi")

    @QtCore.pyqtSlot()
    def update_GUI(self):
        str_cur_date, str_cur_time, _ = get_current_date_time()
        self.qlbl_cur_date_time.setText(
            "%s    %s" % (str_cur_date, str_cur_time)
        )
        self.qlbl_update_counter.setText("%i" % qdev_ard.update_counter_DAQ)
        self.qlbl_DAQ_rate.setText(
            "DAQ: %.1f Hz" % qdev_ard.obtained_DAQ_rate_Hz
        )
        if log.is_recording():
            self.qlbl_recording_time.setText(log.pretty_elapsed())

        self.qlin_ds18b20_temp.setText("%.1f" % state.ds18b20_temp)
        self.qlin_dht22_temp.setText("%.1f" % state.dht22_temp)
        self.qlin_dht22_humi.setText("%.1f" % state.dht22_humi)

        if state.is_valve_open:
            self.LED_is_valve_open.setText("1")
            self.LED_is_valve_open.setChecked(True)
        else:
            self.LED_is_valve_open.setText("0")
            self.LED_is_valve_open.setChecked(False)

    @QtCore.pyqtSlot()
    def update_chart(self):
        if DEBUG:
            tprint("update_chart")

        for tscurve in self.tscurves:
            tscurve.update()


# ------------------------------------------------------------------------------
#   Program termination routines
# ------------------------------------------------------------------------------


def stop_running():
    app.processEvents()
    qdev_ard.quit()
    log.close()

    print("Stopping timers................ ", end="")
    timer_GUI.stop()
    timer_charts.stop()
    print("done.")


@QtCore.pyqtSlot()
def notify_connection_lost():
    stop_running()

    window.qlbl_title.setText("! ! !    LOST CONNECTION    ! ! !")
    str_cur_date, str_cur_time, _ = get_current_date_time()
    str_msg = "%s %s\nLost connection to Arduino." % (
        str_cur_date,
        str_cur_time,
    )
    print("\nCRITICAL ERROR @ %s" % str_msg)
    reply_ = QtWid.QMessageBox.warning(
        window, "CRITICAL ERROR", str_msg, QtWid.QMessageBox.Ok
    )

    if reply_ == QtWid.QMessageBox.Ok:
        pass  # Leave the GUI open for read-only inspection by the user


@QtCore.pyqtSlot()
def about_to_quit():
    print("\nAbout to quit")
    stop_running()
    ard.close()


# ------------------------------------------------------------------------------
#   Your Arduino update function
# ------------------------------------------------------------------------------


def DAQ_function():
    # Date-time keeping
    str_cur_date, str_cur_time, str_cur_datetime = get_current_date_time()

    # Query the Arduino for its state
    success_, tmp_state = ard.query_ascii_values("?", delimiter="\t")
    if not (success_):
        dprint(
            "'%s' reports IOError @ %s %s"
            % (ard.name, str_cur_date, str_cur_time)
        )
        return False

    # Parse readings into separate state variables
    try:
        (
            state.time,
            state.ds18b20_temp,
            state.dht22_temp,
            state.dht22_humi,
            state.is_valve_open,
        ) = tmp_state
        state.time /= 1000  # Arduino time, [msec] to [s]
        state.is_valve_open = bool(state.is_valve_open)
    except Exception as err:
        pft(err, 3)
        dprint(
            "'%s' reports IOError @ %s %s"
            % (ard.name, str_cur_date, str_cur_time)
        )
        return False

    # We will use PC time instead
    state.time = time.perf_counter()

    # Add readings to chart histories
    window.tscurve_ds18b20_temp.appendData(state.time, state.ds18b20_temp)
    window.tscurve_dht22_temp.appendData(state.time, state.dht22_temp)
    window.tscurve_dht22_humi.appendData(state.time, state.dht22_humi)

    # Logging to file
    log.update(filepath=str_cur_datetime + ".txt", mode="w")

    # Return success
    return True


def write_header_to_log():
    log.write("[HEADER]\n")
    log.write(window.qtxt_comments.toPlainText())
    log.write("\n\n[DATA]\n")
    log.write("time\tDS18B20 temp.\tDHT22 temp.\tDHT22 humi.\tvalve\n")
    log.write("[s]\t[±0.5 °C]\t[±0.5 °C]\t[±3 pct]\t[0/1]\n")


def write_data_to_log():
    log.write(
        "%.1f\t%.1f\t%.1f\t%.1f\t%i\n"
        % (
            log.elapsed(),
            state.ds18b20_temp,
            state.dht22_temp,
            state.dht22_humi,
            state.is_valve_open,
        )
    )


# ------------------------------------------------------------------------------
#   Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Set priority of this process to maximum in the operating system
    print("PID: %s\n" % os.getpid())
    try:
        proc = psutil.Process(os.getpid())
        if os.name == "nt":
            proc.nice(psutil.REALTIME_PRIORITY_CLASS)  # Windows
        else:
            proc.nice(-20)  # Other
    except:
        print("Warning: Could not set process to maximum priority.\n")

    # --------------------------------------------------------------------------
    #   Connect to Arduino
    # --------------------------------------------------------------------------

    ard = Arduino(name="Ard", connect_to_specific_ID="Ambre chamber")
    ard.serial_settings["baudrate"] = 115200
    ard.auto_connect()

    if not (ard.is_alive):
        print("\nCheck connection and try resetting the Arduino.")
        print("Exiting...\n")
        sys.exit(0)

    # Get the initial state of the valve control
    success, reply = ard.query("th?")
    if success:
        state.humi_threshold = float(reply)

    success, reply = ard.query("open when super humi?")
    if success:
        state.open_valve_when_super_humi = bool(int(reply))

    # --------------------------------------------------------------------------
    #   Create application and main window
    # --------------------------------------------------------------------------
    QtCore.QThread.currentThread().setObjectName("MAIN")  # For DEBUG info

    app = QtWid.QApplication(sys.argv)
    app.aboutToQuit.connect(about_to_quit)

    window = MainWindow()

    # --------------------------------------------------------------------------
    #   File logger
    # --------------------------------------------------------------------------

    log = FileLogger(
        write_header_function=write_header_to_log,
        write_data_function=write_data_to_log,
    )
    log.signal_recording_started.connect(
        lambda filepath: window.qpbt_record.setText(
            "Recording to file: %s" % filepath
        )
    )
    log.signal_recording_stopped.connect(
        lambda: window.qpbt_record.setText("Click to start recording to file")
    )

    # --------------------------------------------------------------------------
    #   Set up multithreaded communication with the Arduino
    # --------------------------------------------------------------------------

    # Create QDeviceIO
    qdev_ard = QDeviceIO(ard)

    # Create workers
    # fmt: off
    qdev_ard.create_worker_DAQ(
        DAQ_function             = DAQ_function,
        DAQ_interval_ms          = DAQ_INTERVAL_MS,
        critical_not_alive_count = 1,
        debug                    = DEBUG,
    )
    # fmt: on
    qdev_ard.create_worker_jobs()

    # Connect signals to slots
    qdev_ard.signal_DAQ_updated.connect(window.update_GUI)
    qdev_ard.signal_connection_lost.connect(notify_connection_lost)

    # Start workers
    qdev_ard.start(DAQ_priority=QtCore.QThread.TimeCriticalPriority)

    # --------------------------------------------------------------------------
    #   Timers
    # --------------------------------------------------------------------------

    timer_GUI = QtCore.QTimer()
    timer_GUI.timeout.connect(window.update_GUI)
    timer_GUI.start(100)

    timer_charts = QtCore.QTimer()
    timer_charts.timeout.connect(window.update_chart)
    timer_charts.start(CHART_INTERVAL_MS)

    # --------------------------------------------------------------------------
    #   Start the main GUI event loop
    # --------------------------------------------------------------------------

    window.show()
    sys.exit(app.exec_())
