#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import
import time
from ctypes import cdll, c_double
'''
##########################
#         Define         #
##########################

##########################
#        Function        #
##########################
pattern_dsp = [ ['PRBS31'   , 0x00],
                ['PRBS7'    , 0x01],
                ['PRBS9_5'  , 0x02],
                ['PRBS9_4'  , 0x03],
                ['PRBS11'   , 0x04],
                ['PRBS13'   , 0x05],
                ['PRBS15'   , 0x06],
                ['PRBS23'   , 0x07],
                ['PRBS58'   , 0x08],
                ['PRBS16'   , 0x09],
                ['SSPRQ'    , 0x50]]

##########################
#         Class          #
##########################
class PCB_Level(object):
    # print("Import - Triggered_Module_Procedure")
    def __init__(self, i2c_interface):
        # Instance Attribute
        self.i2c_interface = i2c_interface
        self.count = 0
    
    def Method_List(self):
        print("------------------------------------------------------")
        print(" 0. Exit")
        print(" 1. dsp_mode_select")
        print(" 2. dsp_mcu_info_update")
        print(" 3. dsp_link_status_update")
        print(" 4. -")
        print(" 5. -")
        print(" 6. -")
        print(" 7. -")
        print(" 8. -")
        print(" 9. -")
        print("------------------------------------------------------")

    def dsp_mode_select(self):
        while(1):
            print("------------------------------------------------------")
            print(" 0. Exit")
            print(" 1. MISSION_MODE(400G)")
            print(" 2. LINE_PRBS(400G)")
            print(" 3. HOST_PRBS(400G)")
            print(" 4. MISSION_MODE(200G)")
            print(" 5. LINE_PRBS(200G)")
            print("------------------------------------------------------")
            Type = input("dsp_mode_select: ")
            self.i2c_interface.I2C_PAGE_SELECT([0xFF])
            if Type == 1:
                self.i2c_interface.I2C_WRITE(0x80, [0x50])
                self.i2c_interface.I2C_WRITE(0x81, [0x01])
            elif Type == 2:
                self.i2c_interface.I2C_WRITE(0x80, [0x51])
                self.i2c_interface.I2C_WRITE(0x81, [0x01])
            elif Type == 3:
                self.i2c_interface.I2C_WRITE(0x80, [0x52])
                self.i2c_interface.I2C_WRITE(0x81, [0x01])
            elif Type == 4:
                self.i2c_interface.I2C_WRITE(0x80, [0xA0])
                self.i2c_interface.I2C_WRITE(0x81, [0x01])
            elif Type == 5:
                self.i2c_interface.I2C_WRITE(0x80, [0xA1])
                self.i2c_interface.I2C_WRITE(0x81, [0x01])
            else:
                break
        
    def dsp_mcu_info_update(self):
        print("dsp_mode_select")
        self.i2c_interface.I2C_PAGE_SELECT([0xFF])
        self.i2c_interface.I2C_WRITE(0x82, [0x01])

    def dsp_link_status_update(self):
        print("dsp_link_status_update")
        self.i2c_interface.I2C_PAGE_SELECT([0xFF])
        self.i2c_interface.I2C_WRITE(0x83, [0x01])

    def dsp_line_prbs_pattern_select(self):
        Type = input("line_prbs_pattern_select: ")
        # for i in range(10):
            # print("{} = {} ".format(pattern_dsp[i,0], pattern_dsp[i,1]))
            # print("%s = %d " %pattern_dsp[i,0])  %pattern_dsp[i,1])
        self.i2c_interface.I2C_PAGE_SELECT([0xFF])
        self.i2c_interface.I2C_WRITE(0x84, [Type])

    def dsp_host_prbs_pattern_select(self):
        Type = input("host_prbs_pattern_select: ")
        # for i in range(10):
            # print("{} = {} ".format(pattern_dsp[i,0], pattern_dsp[i,1]))
        self.i2c_interface.I2C_PAGE_SELECT([0xFF])
        self.i2c_interface.I2C_WRITE(0x85, [Type])
'''
