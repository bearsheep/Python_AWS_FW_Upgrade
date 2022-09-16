# -*- coding: utf-8 -*-

# ==========================================================================
# IMPORTS
# ==========================================================================
from __future__ import division, with_statement, print_function
import sys
import struct
import math
import time
import string
import binascii
from datetime import datetime
from functools import wraps


def retry(ExceptionToCheck=Exception, tries=3, delay=2, backoff=1, logger=None):
    """Retry calling the decorated function using an exponential backoff.
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


class FirmwareUpgradeBase(object):

    def __init__(self, i2c_dongle, filename, password=int('C24F4F54', 16), retry_if_error=True):
        self.i2c_dongle = i2c_dongle
        self.buffer_size = 256
        self.app_addr = 0xA0
        self.bootloader_addr = 0x36
        self.file_name = filename
        self.data_to_send = None
        self.file_size = 0
        self.file_crc32 = 0
        self.module_number = ''
        self.password = password
        self.retry = retry_if_error

    def init(self):
        # open i2c devices
        self.i2c_dongle.open_device()

    @staticmethod
    def __to_version_str(v):
        return '%d.%02d' % (v >> 8, v & 0xff)

    @staticmethod
    def __progressbar(cur, total):
        percent = '{:.2%}'.format(cur / total)
        sys.stdout.write('\r')
        sys.stdout.write("[%-50s] %s" %
                         ('=' * int(math.floor(cur * 50 / total)), percent))
        sys.stdout.flush()

    @staticmethod
    def _wait_ms(milliseconds):
        time.sleep(milliseconds / 1000)

    def _check_cmd(self, addr, expects, timeout_ms=1000, **kwargs):
        if not isinstance(expects, list):
            raise TypeError("type for 'response' must be list")

        kwargs.setdefault('cmd', expects[0])
        timeout = time.time() + timeout_ms / 1000  # seconds
        while time.time() < timeout:
            self._wait_ms(25)
            (count, data_in) = self.i2c_dongle.read(addr, None, len(expects), **kwargs)
            if count == len(expects) and data_in == expects:
                return True
        else:
            return False

    def verify_file_content(self):
        vendor_info = VendorInfo()
        fw_data = None

        with open(self.file_name, 'rb') as file:
            vendor_info_data = file.read(64)
            if len(vendor_info_data) == 0:
                raise Exception("Verify file error: empty file")

            vendor_info.unpack(vendor_info_data)

            file.seek(64)
            fw_data = file.read()

        if not fw_data or vendor_info.file_size != len(fw_data) or \
                vendor_info.file_crc32 != binascii.crc32(fw_data) & 0xFFFFFFFF:
            raise Exception('Verify file error: invalid file selected')

        if not self.verify_firmware_type(vendor_info.firmware_type_name) or \
                not self.verify_module_number(vendor_info.module_number):
            raise Exception('Verify file error: invalid file selected')

        # print('Upgrade info: %s %s v%s' % (vendor_info.module_number, vendor_info.firmware_type_name, self.__to_version_str(vendor_info.firmware_version)))

        self.prepare_upgrading(fw_data, vendor_info.firmware_type, vendor_info.firmware_type_name,
                               vendor_info.offset_addr, vendor_info.module_number)

    def verify_firmware_type(self, firmware_type_name):
        return False

    def verify_module_number(self, module_number):
        timeout = time.time() + 20000 / 1000  # seconds
        while time.time() < timeout:
            (count, data_in) = self.__verify_module_number_app(module_number)
            if count != 0 and data_in != [0xFF] * count and data_in != [0x00] * count:
                return filter(lambda x: x in set(string.printable),
                              ''.join([chr(d) for d in data_in])).upper() == module_number

            (count, data_in) = self.__verify_module_number_bootloader()
            if count != 0 and data_in != [0xFF] * count and data_in != [0x00] * count:
                return filter(lambda x: x in set(string.printable),
                              ''.join([chr(d) for d in data_in])).upper() == module_number

            self._wait_ms(1000)
        raise Exception('ERROR: verify file timeout.')

    def __verify_module_number_app(self, module_number):
        if module_number.find('100G') != -1 or module_number.find('50G') != -1:  # 100G/50G
            reg_addr = 0x7B
        else:
            reg_addr = 0x7A
        password = [0xC1, 0x4D, 0x41, 0x5A]
        self.i2c_dongle.write(self.app_addr, reg_addr, password)

        # select page FOh
        data_out = [0xF0]
        self.i2c_dongle.write(self.app_addr, 0x7F, data_out)

        # read 32 bytes module number and check
        (count, data_in) = self.i2c_dongle.read(self.app_addr, 0xC0, 32)
        return (count, data_in)

    def __verify_module_number_bootloader(self):
        # read 32 bytes module number and check
        self.i2c_dongle.write(self.bootloader_addr, None, [0x74])
        self._wait_ms(40)
        (count, data_in) = self.i2c_dongle.read(self.bootloader_addr, None, 32, cmd=0x74)
        return (count, data_in)

    def prepare_upgrading(self, file_data, firmware_type, firmware_type_name, offset_addr, module_number):
        self.data_to_send = file_data
        self.image = firmware_type & 0xFF
        self.image_addr = offset_addr
        self.firmware_type_name = firmware_type_name
        self.module_number = module_number

    def calc_file_size_crc(self):
        # try to pad 0xFF
        num_padding_bytes = self.buffer_size - len(self.data_to_send) % self.buffer_size
        if num_padding_bytes != self.buffer_size:
            self.data_to_send += struct.pack('B', 0xFF) * num_padding_bytes

        self.file_size = len(self.data_to_send)
        self.file_crc32 = binascii.crc32(self.data_to_send) & 0xFFFFFFFF

    def send_file_data(self):
        # send file blocks
        trans_num = 0
        max_trans_num = math.ceil(self.file_size / self.buffer_size)
        while trans_num < max_trans_num:
            filedata = self.data_to_send[trans_num * self.buffer_size: (trans_num + 1) * self.buffer_size]

            # Write the data to the bus
            total_bytes = self.buffer_size + 4
            data_out = [0xFF] * total_bytes
            data_out[0] = 0x21
            data_out[1:3] = [ord(t) for t in struct.pack('>H', trans_num + 1)]
            data_out[3:len(filedata) + 3] = [ord(d) for d in filedata]
            checksum = sum(data_out[:-1]) & 0xFF
            data_out[total_bytes - 1] = checksum

            res = self.i2c_dongle.write(self.bootloader_addr, None, data_out)

            if res != 0:
                raise Exception("\nerror: write data error")

            trans_num = trans_num + 1

            self.__progressbar(trans_num, max_trans_num)

            if not self._check_cmd(self.bootloader_addr, [0x21], 100):
                raise Exception("\nerror: ACK error")

    def send_total_file_size(self):
        data_out = [0] * 6
        data_out[0] = 0x13
        data_out[1:5] = [ord(d) for d in struct.pack('>I', self.file_size)]
        data_out[5] = sum(data_out) & 0xFF

        self.i2c_dongle.write(self.bootloader_addr, None, data_out)
        if not self._check_cmd(self.bootloader_addr, [0x13]):
            raise Exception("ERROR: send file length error.")

    def send_file_crc32(self):
        data_out = [0] * 6
        data_out[0] = 0x14
        data_out[1:5] = [ord(d) for d in struct.pack('>I', self.file_crc32)]
        data_out[5] = sum(data_out) & 0xFF

        self.i2c_dongle.write(self.bootloader_addr, None, data_out)
        if not self._check_cmd(self.bootloader_addr, [0x14]):
            raise Exception("ERROR: send file crc32 error.")

    def unlock_bootloader(self):
        timeout = time.time() + 20000 / 1000  # seconds
        while time.time() < timeout:
            if self.module_number.find('100G') != -1 or self.module_number.find('50G') != -1:  # 100G/50G
                reg_addr = 0x7B
            else:
                reg_addr = 0x7A
            password = [ord(d) for d in struct.pack('>I', self.password)]
            self.i2c_dongle.write(self.app_addr, reg_addr, password)

            self._wait_ms(10)

            data_out = [0x10, 0x42, 0x4F, 0x4F, 0x54]
            self.i2c_dongle.write(self.bootloader_addr, None, data_out)
            self._wait_ms(500)
            (count, data_in) = self.i2c_dongle.read(self.bootloader_addr, None, 1, cmd=0x10)
            if count == 1 and data_in[0] == 0x10:
                break
        else:
            raise Exception("ERROR: bootloader unlock error.")

    def choose_image_to_upgrade(self):
        data_out = [0x11, self.image]

        self.i2c_dongle.write(self.bootloader_addr, None, data_out)
        if not self._check_cmd(self.bootloader_addr, [0x11]):
            raise Exception("ERROR: choose image to upgrade error.")

    def flash_addr(self):
        data_out = [0] * 6
        data_out[0] = 0x12
        data_out[1:5] = [ord(d) for d in struct.pack('>I', self.image_addr)]
        data_out[5] = sum(data_out) & 0xFF

        self.i2c_dongle.write(self.bootloader_addr, None, data_out)
        if not self._check_cmd(self.bootloader_addr, [0x12]):
            raise Exception("ERROR: flash addr error.")

    def backup_data(self):
        pass

    def _internal_backup_data(self, command, wait_seconds=5):
        data_out = [command]
        self.i2c_dongle.write(self.bootloader_addr, None, data_out)

        if not self._check_cmd(self.bootloader_addr, [command], wait_seconds * 1000):
            raise Exception("ERROR: backup data error.")

    def erase_flash(self):
        self._internal_erase_flash()

    def _internal_erase_flash(self, wait_seconds=10):
        data_out = [0x20]
        self.i2c_dongle.write(self.bootloader_addr, None, data_out)

        if not self._check_cmd(self.bootloader_addr, [0x20], wait_seconds * 1000):
            raise Exception("ERROR: erase flash error.")

    def validate_crc32(self):
        self._internal_validate_crc32()

    def _internal_validate_crc32(self, wait_seconds=5):
        data_out = [0x22]
        self.i2c_dongle.write(self.bootloader_addr, None, data_out)

        if not self._check_cmd(self.bootloader_addr,
                               [ord(x) for x in struct.pack('>I', self.file_crc32)],
                               wait_seconds * 1000, cmd=0x22):
            raise Exception("ERROR: validate CRC error.")

    def jump_to_image(self):
        # jump to image1
        data_out = [0x30]
        self.i2c_dongle.write(self.bootloader_addr, None, data_out)

    def reset(self):
        data_out = [0x32]
        self.i2c_dongle.write(self.bootloader_addr, None, data_out)

    @retry(tries=3, delay=2)
    def _internal_begin(self):
        self.calc_file_size_crc()

        self.choose_image_to_upgrade()
        self.flash_addr()

        self.send_total_file_size()
        self.send_file_crc32()

        print("> Backup data...")
        self.backup_data()
        print("> Backup data completed.")

        print("> Erasing flash...")
        self.erase_flash()
        print("> Erase completed.")

        print("> Sending data... (%d bytes)" % self.file_size)
        self.send_file_data()
        print("\n> Send data completed.")

        print("> Validating...")
        self.validate_crc32()
        print("> Validate successfully.")

    def begin(self):
        startTime = datetime.now()

        print("Verifying file...")
        self.verify_file_content()
        print("Verify file completed.")

        print("Begin to upgrade...")
        self.unlock_bootloader()

        try:
            if self.retry:
                self._internal_begin()
            else:
                _internal_begin = self._internal_begin.func_closure[3].cell_contents
                _internal_begin(self)
        except Exception as e:
            self.reset()
            raise e

        self.jump_to_image()
        print("\nUPGRADE FINISHED! [Time Elapse: %s]" %
              str(datetime.now() - startTime).split('.')[0])

    def end(self):
        # Close the device
        self.i2c_dongle.close_device()


class VendorInfo(object):

    def unpack(self, info_bytes):
        (file_size, file_crc32, firmware_build_version, firmware_version, firmware_type, offset_addr,
         firmware_type_name, module_number) = struct.unpack('>IIIHHI12s32s', info_bytes)
        self.file_size = file_size
        self.file_crc32 = file_crc32
        self.firmware_build_version = firmware_build_version
        self.firmware_version = firmware_version
        self.firmware_type = firmware_type
        self.offset_addr = offset_addr
        self.firmware_type_name = filter(lambda x: x in set(string.printable), firmware_type_name).upper()
        self.module_number = filter(lambda x: x in set(string.printable), module_number).upper()

        return self
