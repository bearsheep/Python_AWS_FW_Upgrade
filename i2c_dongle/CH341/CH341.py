# -*- coding: utf-8 -*-
import sys
from ctypes import *
import os


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


class Usb_CH341_IIC(Singleton):
    # Load CH341DLL
    Ch341 = None
    IIC_CLK_20kHz = 0x00
    IIC_CLK_100kHz = 0x01  # default
    IIC_CLK_400kHz = 0x02
    IIC_CLK_750kHz = 0x03

    def __init__(self, usb_id):
        try:
            if getattr(sys, 'frozen', False):
                # we are running in a bundle
                # noinspection PyUnresolvedReferences
                cwd = sys._MEIPASS
            else:
                cwd = os.path.dirname(os.path.abspath(__file__))
            Usb_CH341_IIC.Ch341 = windll.LoadLibrary(os.path.join(cwd, 'CH341DLL.DLL'))
        except Exception:
            raise Exception('Load library CH341DLL.DLL error. Make sure you are using 32bit of python!')

        # usb id
        self.usb_id = usb_id
        self.is_device_opened = False

    def open(self, clk):
        mode = {
            20: self.IIC_CLK_20kHz,
            100: self.IIC_CLK_100kHz,
            400: self.IIC_CLK_400kHz,
            750: self.IIC_CLK_750kHz
        }
        self.setmode(mode[clk])

    def setmode(self, IICMode):
        if Usb_CH341_IIC.Ch341.CH341OpenDevice(self.usb_id) != -1:
            # uint8_t CH341SetStream(uint32_t iIndex, uint32_t iMode);
            Usb_CH341_IIC.Ch341.CH341SetStream(self.usb_id, IICMode)
            return 0x00
        else:
            # NO Ch341 Device
            raise IOError('No Ch341 Device found!')

    def write(self, slave_addr, reg_addr, data, num_byte):
        # slave_addr need to write
        # insert these two value to list(data)
        data = data[:]
        if reg_addr is not None:
            data.insert(0, reg_addr)
            num_byte += 1
        data.insert(0, slave_addr)
        num_byte += 1
        # C Array
        writebuff = (c_ubyte * (num_byte))(*data)
        readbuff = (c_ubyte * 1)()

        # uint8_t CH341StreamI2C(uint32_t iIndex, uint32_t iWriteLength, uint8_t *iWriteBuffer, uint32_t iReadLength, uint8_t *oReadBuffer);
        Usb_CH341_IIC.Ch341.CH341StreamI2C(self.usb_id, num_byte, writebuff, 0, readbuff)
        Usb_CH341_IIC.Ch341.CH341SetDelaymS(self.usb_id, 10)

        # write successfully
        return 0x00

    def read(self, slave_addr, reg_addr, data, num_byte):

        readbuff = (c_ubyte * num_byte)()
        if reg_addr is not None:
            writebuff = (c_ubyte * 2)()
            writebuff[0] = slave_addr
            writebuff[1] = reg_addr
        else:
            writebuff = (c_ubyte * 1)()
            writebuff[0] = slave_addr

        # uint8_t CH341StreamI2C(uint32_t iIndex, uint32_t iWriteLength, uint8_t *iWriteBuffer, uint32_t iReadLength, uint8_t *oReadBuffer);
        Usb_CH341_IIC.Ch341.CH341StreamI2C(self.usb_id, len(writebuff), writebuff, num_byte, readbuff)
        Usb_CH341_IIC.Ch341.CH341SetDelaymS(self.usb_id, 10)

        # C Array-->python list
        for i in range(num_byte):
            data.append(readbuff[i])

        # read successfully
        return 0x00

    def close(self):
        # Close Ch341 Device
        if Usb_CH341_IIC.Ch341:
            Usb_CH341_IIC.Ch341.CH341CloseDevice(self.usb_id)
