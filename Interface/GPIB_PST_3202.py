#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########################
#         Import         #
##########################
import pyvisa
import time

##########################
#         Class          #
##########################
class OPEN_VISA(object):
    """
    # self.port: Input channel number. [ex. COM8 = GPIB_PORT(8)]\n
    """
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        # self.device_list = self.rm.list_resources()
        # print("Show COM List:"), self.device_list

    def open(self, port):
        # self.port = "GPIB0::8::INSTR"
        self.port = "GPIB0::" + str.join("", ("%d::INSTR" %port))
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(self.port)
        print("Open"), self.port

    def Show_Voltage(self, channel):
        """
        # Show channel voltage\n
        # channel: Input channel number. [ex. Channel3 = Show_Voltage(3)]\n
        """
        # print "Volatge = ", (self.inst.query(":CHAN3:MEAS:VOLT?"))
        # print":CHAN" + str.join("", ("%d:MEAS:VOLT?" %channel))
        print("Volatge = "), (self.inst.query(":CHAN" + str.join("", ("%d:MEAS:VOLT?" %channel))))
        return (self.inst.query(":CHAN" + str.join("", ("%d:MEAS:VOLT?" %channel))))

    def Show_Current(self, channel, display = 1):
        """
        # Show channel current\n
        # channel: Input channel number. [ex. Channel3 = Show_Current(3)]\n
        """
        # print "Current (CH2)= ", (self.inst.query(":CHAN3:MEAS:CURR?"))
        if display == 1:
            print("Current (CH%d)= " %channel), (self.inst.query(":CHAN" + str.join("", ("%d:MEAS:CURR?" %channel))))
        return (self.inst.query(":CHAN" + str.join("", ("%d:MEAS:CURR?" %channel))))
    
    def Show_IDN(self):
        print(), self.port, ": ", (self.inst.query("*IDN?"))

    def Show_STAT(self):
        # Query power supply on/off status
        # OUTP:STAT ?
        print("Not implemented!")

    def Set_PS_ON_OFF(self, EN):
        '''
        # Set power supply on/off
        # OUTPut:STATe 1
        # OUTPut:STATe 0
        '''
        self.inst.write("OUTPut:STATe " + str(EN))
        if EN == 1:
            Control = 'Enable'
        else:
            Control = 'Disable'
        print(), Control, "Power Supply"

    def Set_Voltage(self, channel, voltage = 0.0):
        # Set voltage
        # ":CHAN3:VOLT 3.30"
        self.inst.write(":CHAN" + str.join("", ("%d:VOLTage" %channel)) + str.join("", (" %f" %voltage)) )

def Show_List():
        """
        # Show COM List e.g. GPIB, RS232, USB, Ethernet\n
        """
        rm = pyvisa.ResourceManager()
        print("Show COM List:"), rm.list_resources()

if __name__ == "__main__":
    print("[Start Script]: GPIB.py")
    print("[End Script]: GPIB.py")
    
    # Test here
    Show_List()
    GPIB8 = OPEN_VISA()
    GPIB8.open(8)
    GPIB8.Set_PS_ON_OFF(1)
    #time.sleep(1)
    # GPIB8.Set_PS_ON_OFF(1)
    # time.sleep(2)

    #GPIB8.Set_PS_ON_OFF(0)
    # GPIB8.Show_STAT
    GPIB8.Set_Voltage(2, 3.30)
    GPIB8.Show_Current(2)
    #GPIB8.Show_Current(3)
