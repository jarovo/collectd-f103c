# F103C Collectd plugin

[![Build Status](https://travis-ci.org/jaryn/collectd-f103c.svg?branch=master)](https://travis-ci.org/jaryn/collectd-f103c)

A collectd plugin for interfacing with the f103c based adc USB module


## About the HW
The module is selled as:

NOYITO USB 10-Channel 12-Bit AD Data Acquisition Module STM32 UART Communication USB to Serial Chip CH340 ADC Module


`lsusb` shows
```
Bus 002 Device 003: ID 1a86:7523 QinHeng Electronics HL-340 USB-Serial adapter
```

linux driver required: `ch341-uart`


## Installation
 * Python is required.
   `sudo apt install -y python3-setuptools`
 * Make sure you have setuptools installed
 * `sudo pip3 install git+git://github.com/jaryn/collectd-f103c.git`
