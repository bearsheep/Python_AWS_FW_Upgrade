# -*- coding: utf-8 -*-
from __future__ import division, with_statement, print_function
import sys
import struct
import time
from datetime import datetime
import math


class FirmwareUpgradeCDB(object):

    def __init__(self, i2c_dongle, filename, hitless_restart, commit_image):
        self.i2c_dongle = i2c_dongle
        self.app_addr = 0xA0
        self.file_name = filename
        self.data_to_send = None
        self.vendor_info_data = None
        self.file_size = 0
        self.block_size = 0
        self.start_command_payload_size = 64
        self.reset_mode = 0x01 if hitless_restart else 0x00
        self.commit_image = commit_image

    def init(self):
        # open i2c devices
        self.i2c_dongle.open_device(bitrate=100)

    def begin(self):
        startTime = datetime.now()
        print("Begin to upgrade...")
        # select page 9Fh
        self.select_page(0x9F)
        # self.send_password()  # remove by Lance, 20210901. CMIS5.0 upgrade FW didn't need password.
        self.read_capabilities()
        self.read_image_file()
        self.send_start_command()
        print("Sending data... (%d bytes)" % len(self.data_to_send))
        # self.write_image_lpl()
        self.write_image_epl()
        print("\nValidating...")
        self.send_complete_command()
        print("Validate successfully.")
        # self.run_fw_image()   # remove by Lance, 20210715.
        if self.commit_image:
            print("Rebooting...")
            self.__wait_reboot()
            print("Commit running image.")
            self.select_page(0x9F)
            self.send_password()
            self.commit_fw_image()
        print("\nUPGRADE FINISHED! [Time Elapse: %s]" % str(datetime.now() - startTime).split('.')[0])

    @staticmethod
    def _wait_ms(milliseconds):
        time.sleep(milliseconds / 1000)

    @staticmethod
    def __progressbar(cur, total):
        percent = '{:.2%}'.format(cur / total)
        sys.stdout.write('\r')
        sys.stdout.write("[%-50s] %s" %
                         ('=' * int(math.floor(cur * 50 / total)), percent))
        sys.stdout.flush()

    def select_page(self, page):
        self.i2c_dongle.write(self.app_addr, 0x7F, [page])

    def send_password(self):
        command_code = [0x00, 0x01]
        command_param = [0x00] * 10
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = 0x04  # LPL Len
        command_param[3] = 0x00  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode
        command_param[6:] = [0x00, 0x00, 0x10, 0x11]  # password
        command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF

        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)

        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

        self.__check_cdb_status()

    def __check_cdb_status(self, timeout_ms=1000):
        status = {
            0x01: 'Success',
            0x40: 'Failed',
            0x41: 'CMD Code unknown',
            0x42: 'Parameter range error or not supported',
            0x43: 'Previous CMD was not aborted',
            0x44: 'CMD checking time out',
            0x45: 'CdbChkCode error',
            0x46: 'Insufficient privilege'
        }

        timeout = time.time() + timeout_ms / 1000  # seconds
        delay_ms = 40
        while True:
            self._wait_ms(delay_ms)
            is_timeout = time.time() > timeout

            # read CDB complete flag
            (count, data_in) = self.i2c_dongle.read(self.app_addr, 8, 1)
            result = count > 0 and (data_in[0] & 0x40) == 0x40
            if not result:
                if is_timeout:
                    raise Exception("\nERROR: CDB command not completed.")
                continue

            # read CDB status
            while True:
                (count, data_in) = self.i2c_dongle.read(self.app_addr, 37, 1)
                result = count > 0 and data_in[0] == 0x01
                if result:
                    return

                if is_timeout:                    
                    if count == 0:
                        raise Exception("\nBusy processing command.")
                    else:
                        raise Exception('\nERROR: CDB command status - [' + status[data_in[0]] + ']')
                
                self._wait_ms(delay_ms)
                is_timeout = time.time() > timeout

    def __wait_reboot(self):
        timeout = time.time() + 40
        delay_ms = 1000
        while True:
            self._wait_ms(delay_ms)
            is_timeout = time.time() > timeout

            count, d = self.i2c_dongle.read(self.app_addr, 0, 1)
            if count > 0:
                break
            if is_timeout:
                raise Exception("\nERROR: Waiting reboot timeout.")

            delay_ms = min(delay_ms * 2, 4000)

    def read_capabilities(self):
        command_code = [0x00, 0x41]
        command_param = [0x00] * 6
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = 0x00  # LPL Len
        command_param[3] = 0xBE  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode

        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)

        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

        self.__check_cdb_status()

        # read start command payload size and block size
        (_, data_in) = self.i2c_dongle.read(self.app_addr, 138, 3)
        self.start_command_payload_size, _, bsize = data_in
        self.block_size = (bsize + 1) * 8

    def read_image_file(self):
        with open(self.file_name, 'rb') as f:
            self.vendor_info_data = f.read(self.start_command_payload_size)
            if len(self.vendor_info_data) == 0:
                raise Exception("empty file")
            
            self.data_to_send = f.read()
            self.file_size = len(self.vendor_info_data) + len(self.data_to_send)

    def send_start_command(self):
        command_code = [0x01, 0x01]

        command_param = [0x00] * (len(self.vendor_info_data) + 14)
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = len(self.vendor_info_data) + 8  # LPL Len
        command_param[3] = 0x00  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode
        command_param[6:10] = [ord(d) for d in struct.pack('>I', self.file_size + 8)]  # image size
        command_param[10:14] = [0x00] * 4  # Reserved
        command_param[14:] = [ord(d) for d in self.vendor_info_data]  # Vendor Data

        command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF

        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)
        self._wait_ms(50)
        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

        self.__check_cdb_status(timeout_ms=10000)

    def write_image_lpl(self):
        command_code = [0x01, 0x03]

        start_addr = 0

        # send file blocks
        trans_num = 0
        block_size_lpl = 116
        max_trans_num = math.ceil(len(self.data_to_send) / block_size_lpl)
        while trans_num < max_trans_num:
            filedata = self.data_to_send[trans_num * block_size_lpl: (trans_num + 1) * block_size_lpl]

            command_param = [0x00] * (len(filedata) + 10)
            command_param[:2] = [0x00] * 2  # EPL Len
            command_param[2] = len(filedata) + 4  # LPL Len
            command_param[3] = 0x00  # CdbCheckCode
            command_param[4] = 0x00  # RLPLLen
            command_param[5] = 0x00  # RLPLChkCode
            command_param[6:10] = [ord(d) for d in struct.pack('>I', start_addr + block_size_lpl * trans_num)]  # addr
            command_param[10:] = [ord(d) for d in filedata]
            command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF

            self.i2c_dongle.write(self.app_addr, 130, command_param)
            # write command code
            self.i2c_dongle.write(self.app_addr, 128, command_code)

            self.__check_cdb_status()

            trans_num = trans_num + 1
            self.__progressbar(trans_num, max_trans_num)

    def write_image_epl(self):
        command_code = [0x01, 0x04]
        addr_offset = 0

        # send file blocks
        trans_num = 0
        max_trans_num = math.ceil(len(self.data_to_send) / self.block_size)
        total_progress = math.ceil(len(self.data_to_send) / 128)
        current_progress = 0
        while trans_num < max_trans_num:
            filedata = self.data_to_send[trans_num * self.block_size: (trans_num + 1) * self.block_size]

            pages = math.ceil(len(filedata) / 128)
            for i in range(int(pages)):
                self.select_page(0xA0 + i)
                self.i2c_dongle.write(self.app_addr, 128, map(ord, filedata[128 * i:128 * (i + 1)]))

                current_progress += 1
                self.__progressbar(current_progress, total_progress)

            command_param = [0x00] * 10
            command_param[:2] = [ord(d) for d in struct.pack('>H', len(filedata))]  # EPL Len
            command_param[2] = 0x04  # LPL Len
            command_param[3] = 0x00  # CdbCheckCode
            command_param[4] = 0x00  # RLPLLen
            command_param[5] = 0x00  # RLPLChkCode
            command_param[6:] = [ord(d) for d in struct.pack('>I', addr_offset)]  # addr
            command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF

            self.select_page(0x9F)
            # write command param
            self.i2c_dongle.write(self.app_addr, 130, command_param)
            # write command code
            self.i2c_dongle.write(self.app_addr, 128, command_code)

            self.__check_cdb_status()

            addr_offset += len(filedata)
            trans_num = trans_num + 1

    def send_complete_command(self):
        command_code = [0x01, 0x07]

        command_param = [0x00] * 6
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = 0  # LPL Len
        command_param[3] = 0xF7  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode

        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)

        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

        self.__check_cdb_status(timeout_ms=20000)

    def run_fw_image(self):
        command_code = [0x01, 0x09]

        command_param = [0x00] * 10
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = 0x04  # LPL Len
        command_param[3] = 0x00  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode
        command_param[6] = 0x00  # Reserved
        command_param[7] = self.reset_mode  # Reset Mode
        command_param[8] = 0x00  # Delay to Reset ms(MSB)
        command_param[9] = 0x00  # Delay to Reset ms(LSB)
        command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF
        
        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)

        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

    def commit_fw_image(self):
        command_code = [0x01, 0x0A]

        command_param = [0x00] * 6
        command_param[:2] = [0x00] * 2  # EPL Len
        command_param[2] = 0x00  # LPL Len
        command_param[3] = 0x00  # CdbCheckCode
        command_param[4] = 0x00  # RLPLLen
        command_param[5] = 0x00  # RLPLChkCode
        command_param[3] = 0xFF - (sum(command_code) + sum(command_param)) & 0xFF

        # write command param
        self.i2c_dongle.write(self.app_addr, 130, command_param)

        # write command code
        self.i2c_dongle.write(self.app_addr, 128, command_code)

        self.__check_cdb_status()

    def end(self):
        # Close the device
        self.i2c_dongle.close_device()


if __name__ == '__main__':
    import argparse
    import os
    # from i2c_dongle import I2C_Dongle_Factory
    from i2c_dongle.I2C_Dongle_Factory import I2C_Dongle_Factory

    parser = argparse.ArgumentParser(
        description='Firmware upgrade program (CDB)'
    )
    parser.add_argument(
        'file',
        help='the file to be sent'
    )
    parser.add_argument(
        '-hr', '--hitless-restart',
        dest='hitless_restart',
        action='store_true',
        help='attempt a hitless restart to the inactive image.'
    )
    parser.add_argument(
        '-c', '--commit-image',
        dest='commit_image',
        action='store_true',
        help='commit firmware image after upgrade.'
    )

    I2C_Dongle_Factory.add_dongle_arguments(parser)

    args = parser.parse_args()

    (_, ext) = os.path.splitext(args.file)
    if ext.lower() != '.bin':
        print("Error: invalid file format")
        sys.exit()

    upgrade = None
    try:
        dongle = I2C_Dongle_Factory.create_dongle_object(args.dongle)(args.port)
        upgrade = FirmwareUpgradeCDB(dongle, args.file, args.hitless_restart, args.commit_image)
        upgrade.init()
        upgrade.begin()
    except EOFError:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        print(ex)
    finally:
        if upgrade:
            upgrade.end()
