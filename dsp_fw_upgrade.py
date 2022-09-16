#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import argparse

from i2c_dongle import I2C_Dongle_Factory
from fw_upgrade import FirmwareUpgradeBase

class DSP_FirmwareUpgrade(FirmwareUpgradeBase):
    def verify_firmware_type(self, firmware_type_name):
        return firmware_type_name.startswith('DSP')

    def backup_data(self):
        self._internal_backup_data(0x44, 20)
    
    def erase_flash(self):
        self._internal_erase_flash(10)

    def validate_crc32(self):
        self._internal_validate_crc32(10)

# ==========================================================================
# MAIN PROGRAM
# ==========================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='DSP Firmware upgrade program')

    parser.add_argument(
        'file',
        help='the file to be sent'
    )
    parser.add_argument(
        '-d', '--dongle',
        dest='dongle',
        help='the usage of communication interface.',
        choices=I2C_Dongle_Factory.get_dongles()
    )
    parser.add_argument(
        '-pwd', '--password',
        dest='password',
        default='C24F4F54',
        type=lambda x: int(x, 16),
        help='the password(hex string) of module bootloader protected.'
    )
    parser.add_argument(
        '--port', '-p',
        dest='port',
        help='the port number which I2C dongle devices are attached'
    )

    args = parser.parse_args()

    _, ext = os.path.splitext(args.file)
    if ext.lower() != '.bin':
        print("Error: invalid file format")
        sys.exit()

    upgrade = None
    try:
        dongle = I2C_Dongle_Factory.create_dongle_object(args.dongle)(args.port)
        upgrade = DSP_FirmwareUpgrade(dongle, args.file, args.password)
        upgrade.init()
        upgrade.begin()
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        print(ex)
    finally:
        upgrade.end()
