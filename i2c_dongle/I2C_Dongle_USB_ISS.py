from __future__ import division, print_function
import math
import sys
import serial.tools.list_ports
from usb_iss import UsbIss, defs, UsbIssError
from usb_iss.driver import Driver
from usb_iss.i2c import I2C

from I2C_Dongle import I2C_Dongle


class MyDriver(Driver):
    def __init__(self, verbose=False):
        super(MyDriver, self).__init__(verbose)

    def write_cmd(self, command, data=None):
        if self._serial is None:
            raise UsbIssError("Serial port has not been opened")

        if data is None:
            data = []

        if self.verbose:
            print("USB_ISS write: ", end="")
            print(" ".join(["%02X" % byte for byte in [command] + data]))

        self._serial.reset_input_buffer()

        self._serial.write(bytearray([command] + data))


class I2C_Dongle_USBISS(I2C_Dongle):
    def __init__(self, port):
        try:
            self.port = int(port) if port else 0
        except ValueError:
            self.port = 0
        self.iss = None

    def get_port(self):
        if self.port != 0: return 'COM' + str(self.port)

        plist = list(serial.tools.list_ports.comports())
        for p in plist:
            if sys.platform.startswith('win32'):
                if p.vid == 0x04D8 and p.pid == 0xFFEE:
                    return p.device
            elif sys.platform.startswith('linux'):
                if 'USB VID:PID=04d8:ffee' in p[2]:
                    return p[0]
        raise UsbIssError("\nCan't find usb-iss device!\n")

    def open_device(self, bitrate=400):
        try:
            self.iss = UsbIss()
            self.iss._drv = MyDriver()
            self.iss.i2c = I2C(self.iss._drv)
            self.iss.open(self.get_port())
            self.iss.setup_i2c(clock_khz=bitrate)
        except Exception:
            raise UsbIssError("\ninitial usb-iss device error!\n")

    def write(self, slave_addr, reg_addr, data, **kwargs):
        try:
            data_write = data[:]
            len_take = 15 if reg_addr is None else 14
            end = math.ceil(len(data_write) / len_take)
            for t in range(int(end)):
                data_out = data_write[t * len_take:(t + 1) * len_take]
                if t == 0:
                    if reg_addr is not None: data_out.insert(0, reg_addr)  # reg_addr
                    data_out.insert(0, slave_addr)  # slave_addr
                    data_out.insert(0, 0x30 + len(data_out) - 1)  # write length
                    data_out.insert(0, 0x01)  # i2c start
                else:
                    data_out.insert(0, 0x30 + len(data_out) - 1)  # write length

                if t == end - 1:
                    data_out.append(0x03)  # i2c stop

                self.iss.i2c.direct(data_out)
        except:
            return -1
        return 0

    def read(self, slave_addr, reg_addr, num_bytes, **kwargs):
        data_in = []

        try:
            read_bytes_per_time = 16
            max_loop_num = math.ceil(num_bytes / read_bytes_per_time)
            num = 0
            while num < max_loop_num:
                if num_bytes - num * read_bytes_per_time < read_bytes_per_time:
                    read_bytes_per_time = num_bytes - num * read_bytes_per_time

                data_out = []
                if num == max_loop_num - 1:
                    data_out.insert(0, defs.I2CDirect.STOP)
                    data_out.insert(0, defs.I2CDirect.READ1)
                    data_out.insert(0, defs.I2CDirect.NACK)
                    if read_bytes_per_time > 1:
                        data_out.insert(0, 0x20 + read_bytes_per_time - 2)
                else:
                    data_out.insert(0, 0x20 + read_bytes_per_time - 1)
                if num == 0:
                    data_out.insert(0, slave_addr | 0x01)
                    data_out.insert(0, defs.I2CDirect.WRITE1)
                    if reg_addr is not None:
                        data_out.insert(0, defs.I2CDirect.RESTART)
                        data_out.insert(0, reg_addr)
                        data_out.insert(0, slave_addr)
                        data_out.insert(0, defs.I2CDirect.WRITE2)
                    data_out.insert(0, defs.I2CDirect.START)

                data_in += self.iss.i2c.direct(data_out)

                num += 1
        except:
            del data_in[:]

        return len(data_in), data_in

    def close_device(self):
        if self.iss: self.iss.close()
