
import time
from CH341 import CH341
from I2C_Dongle import I2C_Dongle

class I2C_Dongle_CH341(I2C_Dongle):
    def __init__(self, port):
        try:
            port = int(port) if port else 0
        except ValueError:
            port = 0
        self.IIC_Ch341 = CH341.Usb_CH341_IIC(port)

    
    def open_device(self, bitrate=20):
        self.IIC_Ch341.open(bitrate)

    def write(self, slave_addr, reg_addr, data, **kwargs):
        return self.IIC_Ch341.write(slave_addr, reg_addr, data, len(data))
    
    def read(self, slave_addr, reg_addr, num_bytes, **kwargs):
        data_in = []
        self.IIC_Ch341.read(slave_addr, reg_addr, data_in, num_bytes)
        return (len(data_in), data_in)
    
    def close_device(self):
        self.IIC_Ch341.close()
