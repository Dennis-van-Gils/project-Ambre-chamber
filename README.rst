.. image:: https://requires.io/github/Dennis-van-Gils/project-Ambre-chamber/requirements.svg?branch=master
    :target: https://requires.io/github/Dennis-van-Gils/project-Ambre-chamber/requirements/?branch=master
    :alt: Requirements Status
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/project-Ambre-chamber/blob/master/LICENSE.txt

Ambre chamber
=======================
*A Physics of Fluids project.*

A temperature and humidity controlled chamber build from an Adafruit Feather M4
Express micro-controller board and a DHT22 and DS18B20 sensor. Cooling is
provided by Peltier elements, which are controlled by an independent power
supply. The humidity is regulated by a solenoid valve connected up to the N2 gas
line.

- Github: https://github.com/Dennis-van-Gils/project-Ambre-chamber

.. image:: https://raw.githubusercontent.com/Dennis-van-Gils/project-Ambre-chamber/master/images/screenshot.png

Instructions
============
Download the `latest release <https://github.com/Dennis-van-Gils/project-Ambre-chamber/releases/latest>`_
and unpack to a folder onto your drive.

Flashing the firmware
---------------------

Double click the reset button of the Feather while plugged into your PC. This
will mount a drive called `FEATHERBOOT`. Copy
`src_mcu/_build_Feather_M4/CURRENT.UF2 <https://github.com/Dennis-van-Gils/project-Ambre-chamber/raw/master/src_mcu/_build_Feather_M4/CURRENT.UF2>`_
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
