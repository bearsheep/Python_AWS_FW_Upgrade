from i2c_dongle.I2C_Dongle import I2C_Dongle
from smbus2 import SMBus, i2c_msg


class I2CSMBUS(I2C_Dongle):
    def __init__(self, busnum):
        tips = '''
***
Warning: This program has been tested on RaspiberryPi 4B only! It uses smbus2(https://github.com/kplindegaard/smbus2)
package instend of the python-smbus package.
***
        '''
        print(tips)
        try:
            self.busnum = int(busnum) if busnum else 1
        except ValueError:
            self.busnum = 1
        self.bus = None

    def write(self, slave_addr, reg_addr, data):
        """
            Write data to i2c device.
            return zero if success, and non-zero if failed.
        """
        try:
            slave_addr >>= 1
            if reg_addr is not None:
                data.insert(0, reg_addr)

            msg = i2c_msg.write(slave_addr, data)
            self.bus.i2c_rdwr(msg)
            return 0
        except:
            return -1

    def read(self, slave_addr, reg_addr, num_bytes):
        """
            Read data from i2c device.
            return tuple (length, data), where data is a List object and
            length is an integer.
        """
        try:
            slave_addr >>= 1
            if reg_addr is not None:
                write = i2c_msg.write(slave_addr, [reg_addr])
                read = i2c_msg.read(slave_addr, num_bytes)
                self.bus.i2c_rdwr(write, read)
            else:
                read = i2c_msg.read(slave_addr, num_bytes)
                self.bus.i2c_rdwr(read)

            data_in = list(read)
            return len(data_in), data_in
        except:
            return 0, []

    def open_device(self, bitrate=100):
        """open i2c device"""
        self.bus = SMBus(self.busnum)

    def close_device(self):
        if self.bus:
            self.bus.close()
