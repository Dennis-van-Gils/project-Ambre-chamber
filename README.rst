.. image:: https://requires.io/github/Dennis-van-Gils/project-BME280-DS18B20-logger/requirements.svg?branch=master
    :target: https://requires.io/github/Dennis-van-Gils/project-BME280-DS18B20-logger/requirements/?branch=master
    :alt: Requirements Status
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/project-BME280-DS18B20-logger/blob/master/LICENSE.txt

BME280 & DS18B20 logger
=======================
*A Physics of Fluids project.*

A temperature, humidity and pressure data logger build from an Adafruit Feather
M4 Express micro-controller board and a BME280 and DS18B20 sensor with a
graphical user interface in Python.

- Github: https://github.com/Dennis-van-Gils/project-BME280-DS18B20-logger

.. image:: https://raw.githubusercontent.com/Dennis-van-Gils/project-BME280-DS18B20-logger/master/images/screenshot.png

Instructions
============
Download the `latest release <https://github.com/Dennis-van-Gils/project-BME280-DS18B20-logger/releases/latest>`_
and unpack to a folder onto your drive.

Flashing the firmware
---------------------

Double click the reset button of the Feather while plugged into your PC. This
will mount a drive called `FEATHERBOOT`. Copy
`src_mcu/_build_Feather_M4/CURRENT.UF2 <https://github.com/Dennis-van-Gils/project-BME280-DS18B20-logger/raw/master/src_mcu/_build_Feather_M4/CURRENT.UF2>`_
onto the Featherboot drive. It will restart automatically with the new
firmware.

Running the application
-----------------------

Preferred Python distributions:
    * `Anaconda <https://www.anaconda.com>`_
    * `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_

Open `Anaconda Prompt` and navigate to the unpacked folder. Run the following to
install the necessary packages: ::

    cd src_python
    pip install -r requirements.txt
    
Now you can run the application: ::

    python main.py

LED status lights
=================

* Solid blue: Booting and setting up
* Solid green: Ready for communication
* Flashing green: Sensor data is being send over USB
