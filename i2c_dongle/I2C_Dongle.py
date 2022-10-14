import abc

class I2C_Dongle(object):
    __metaclass__  = abc.ABCMeta

    @abc.abstractmethod    
    def write(self, slave_addr, reg_addr, data, **kwargs):
        """ 
            Write data to i2c device.
            return zero if success, and non-zero if failed.
        """

    @abc.abstractmethod
    def read(self, slave_addr, reg_addr, num_bytes, **kwargs):
        """
            Read data from i2c device.
            return tuple (length, data), where data is a List object and
            length is an integer.
        """

    @abc.abstractmethod
    def open_device(self, bitrate):
        """open i2c device"""

    @abc.abstractmethod
    def close_device(self):
        """close i2c device"""