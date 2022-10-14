from array import array
from aardvark_py import *
from I2C_Dongle import I2C_Dongle


class I2C_Dongle_Aardvark(I2C_Dongle):
    def __init__(self, port=0):
        try:
            self.port = int(port) if port else 0
        except ValueError:
            self.port = 0
        self.handle = None

    def open_device(self, bitrate=400):
        # open i2c devices
        self.handle = aa_open(self.port)
        if self.handle <= 0:
            print("Unable to open Aardvark device on port %d" % self.port)
            print("Error code = %d" % self.handle)
            raise IOError

        # Ensure that the I2C subsystem is enabled
        aa_configure(self.handle,  AA_CONFIG_SPI_I2C)

        # Enable the I2C bus pullup resistors (2.2k resistors).
        aa_i2c_pullup(self.handle, AA_I2C_PULLUP_BOTH)

        # Enable the Aardvark adapter's power supply.
        aa_target_power(self.handle, AA_TARGET_POWER_BOTH)

        # Set the bitrate
        aa_i2c_bitrate(self.handle, bitrate)

    def write(self, slave_addr, reg_addr, data, **kwargs):
        data_out = array('B', data)
        if reg_addr is not None:
            data_out = array('B', [reg_addr & 0xFF] + data)  
        count = aa_i2c_write(self.handle, slave_addr>>1, AA_I2C_NO_FLAGS, data_out)
        
        return count - len(data_out)
    
    def read(self, slave_addr, reg_addr, num_bytes, **kwargs):
        if reg_addr is not None:
            data_out = array('B', [reg_addr & 0xFF])
            aa_i2c_write(self.handle, slave_addr>>1, AA_I2C_NO_FLAGS, data_out)

        (count, data_in) = aa_i2c_read(self.handle, slave_addr>>1, AA_I2C_NO_FLAGS, num_bytes) 
        return (count, [b for b in data_in])
    
    def close_device(self):
        if self.handle:
            aa_close(self.handle)
