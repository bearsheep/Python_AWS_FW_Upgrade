#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########################
#         Import         #
##########################
import time
# from usb_iss import UsbIss
from usb_iss import UsbIss

# Define #
USB_ISS_Write_delay = 0.01 # SPEC = 80ms in 8 bytes.
USB_ISS_Read_delay = 0.002

##########################
#         Class          #
##########################
class I2C_ISS(object):
    """
        self.port : ex. "COM1"\n
        self.Slave_Addr : Input slave address(8-bit Address).\n
        self.print_debug : Print log = 1; Not to print log = 0; \n
        """
    def __init__(self, port, print_debug = 0, Slave_Addr = 0xA0, speed = 400):
        # Instance Attribute
        self.port = port
        # 7bit Address
        self.Slave_Addr = (Slave_Addr >> 1)
        self.print_debug = print_debug
        self.speed = speed

        self.iss = UsbIss()
        self.iss.open(self.port)
        self.iss.setup_i2c(self.speed)
        #print ("[Interface] Open ") + self.port + "\n"

    def ISS_PORT_CLOSE(self):
        self.iss.close()

    # Basic Function
    def I2C_READ(self, address, number):
        """
        USB-ISS Read
        # byte must be in range(0, 256)
        """
        data = [0]*number
        start = 0
        end = 0
        while(number > 0):
            if number < 60:
                end += number
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read(self.Slave_Addr, address, number)
                break
            else:
                end += 60
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read(self.Slave_Addr, address, 60)
                start += 60
                address += 60
                if((number - 60) >= 0):
                    number -= 60
                if(address >= 256):
                    address -= 128
        
        if self.print_debug == 1:
            print ("Read byte 0x%02X value = " %address + str.join("", ("0x%02X, " %a for a in data[0:end])))
        return data

    def I2C_CURRENT_READ(self, number):
        data = [0]*number
        start = 0
        end = 0
        address = 0
        while(number > 0):
            if number < 60:
                end += number
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read_ad0(self.Slave_Addr, number)
                break
            else:
                end += 60
                #if self.print_debug == 1:
                    #print "start = ", start, "end = ", end, "address = ", address, "number = ", number
                data[start:end] = self.iss.i2c.read_ad0(self.Slave_Addr, 60)
                start += 60
                address += 60
                if((number - 60) >= 0):
                    number -= 60
                if(address >= 256):
                    address -= 128
        return data

    def I2C_WRITE(self, byte, data, write_delay = USB_ISS_Write_delay):
        """
        USB-ISS Write
        """
        ret = 0
        byte_shift = 0
        Start_address = byte
        number_of_byte = len(data)
        # Modify by Lance
        while(1):
            if number_of_byte > 60:
                ret = self.iss.i2c.write(self.Slave_Addr, Start_address, data[(0 + byte_shift):(60 + byte_shift)])
                Start_address += 60
                number_of_byte -= 60
                byte_shift += 60
            else:
                ret = self.iss.i2c.write(self.Slave_Addr, Start_address, data[byte_shift:(byte_shift + number_of_byte)])
                break
        # Modify by Lance
        time.sleep(write_delay)
        if self.print_debug == 1:
            if byte == 0x7F:
                print ("Page select = " + str.join("", ("0x%02X, " %a for a in data)))
            else:
                print ("Write byte 0x%02X value = " %byte + str.join("", ("0x%02X, " %a for a in data)))
        return ret

    # Addictional Function
    def I2C_PAGE_SELECT(self, page, write_delay = USB_ISS_Write_delay):
        data = [0xFF]
        self.I2C_WRITE(0x7F, page, write_delay)
        time.sleep(write_delay)
        data = self.I2C_READ(0x7F, 1)
        if data != page:
            print ("Change Page %s Fail" %hex(data[0]))

    def MODULE_MODE_CONTROL(self, en):
        self.I2C_WRITE(0x7F, [0xE6])
        time.sleep(0.08)
        self.I2C_WRITE(0xF0, en)
        time.sleep(0.08)
        if self.print_debug == 1:
            print("Manual Mode = " + en)

    def I2C_READ_Vendor_Info(self):
        self.I2C_WRITE(0x7F, [0x00])
        time.sleep(USB_ISS_Write_delay)

        # Vendor PN
        TEMP_DATA_Vendor_Info = self.I2C_READ(0x94, 16)
        # Number to ASCII
        for x in range(len(TEMP_DATA_Vendor_Info)):
            TEMP_DATA_Vendor_Info[x] = chr(TEMP_DATA_Vendor_Info[x])
        print(TEMP_DATA_Vendor_Info)

        # Vendor SN
        TEMP_DATA_Vendor_Info = self.I2C_READ(0xA6, 16)
        # Number to ASCII
        for x in range(len(TEMP_DATA_Vendor_Info)):
            TEMP_DATA_Vendor_Info[x] = chr(TEMP_DATA_Vendor_Info[x])
        print(TEMP_DATA_Vendor_Info)

    # For 400G DR4 Only
    def TWI_DSP_Direct_Read(self, reg, reg_name):
        self.I2C_PAGE_SELECT(0xB3)
        self.I2C_WRITE(0xF4, reg)
        time.sleep(USB_ISS_Write_delay)
        self.I2C_WRITE(0xF3, [0x01])
        time.sleep(0.02)
        self.reg = reg_name
        self.data = self.I2C_READ(0xFA, 2)
        #print ("Read Data = "+ str.join("", ("%02X" % a for a in data)))
        print (self.reg +" (Read) = 0x" + str.join("", ("%02X" % a for a in self.data)))

    def TWI_DSP_Direct_Wirte(self, reg, reg_name, Write_data):
        self.I2C_PAGE_SELECT(0xB3)
        self.I2C_WRITE(0xF4, reg)
        time.sleep(USB_ISS_Write_delay)
        self.I2C_WRITE(0xFA, Write_data)
        time.sleep(USB_ISS_Write_delay)
        self.I2C_WRITE(0xF3, [0x00])
        time.sleep(0.02)
        self.reg = reg_name
        self.data = self.I2C_READ(0xFA, 2)
        #print ("Write Data", str.join("",("%02x" % a for a in self.data)))
        print (self.reg +" (Write) = 0x" + str.join("", ("%02X" % a for a in self.data)))

    def SW_RESET(self, delay):
        print ('Software Reset!')
        self.I2C_WRITE(26, [0x08])
        print ('wait ')+ str(delay)+'s'
        time.sleep(delay)

    def Quick_HPMode(self, delay):
        print ('Quick_HPMode!')
        self.I2C_WRITE(26, [0x00])
        print ('wait ')+ str(delay)+'s'
        time.sleep(delay)

    def Write_Password(self):
        print ('Write_Password!\n')
        self.I2C_WRITE(0x7A, [0x43, 0x4A, 0x2D, 0x4C])
        time.sleep(0.02)

    def Write_Password_Bizlink(self):
        print ('Write_Password!\n')
        self.I2C_WRITE(0x7A, [0x8A, 0x0B, 0x0C, 0x0D])
        time.sleep(0.02)

if __name__ == "__main__":
    print("[Start Script]: Interface.py")
    count = 0

    # I2C slave test
    # setup i2c master speed
    test_speed = 400
    I2C_ISS_1 = I2C_ISS('COM7', 1, 0xA0, test_speed)
    #I2C_ISS_2 = I2C_ISS('COM6', 1, 0xA0, test_speed)
    
    # Need test each item when module power up!!!
    # 01-04-22 current read abnormal at first current read
    if(0):
        # step 1: one byte
        # I2C_ISS_1.I2C_WRITE(0x80, [0x10])
        # I2C_ISS_1.I2C_READ(0x00, 1)
        I2C_ISS_1.I2C_CURRENT_READ(1)
    elif (1):
        # step 2: two byte
        # I2C_ISS_1.I2C_WRITE(0x80, [0x10, 0x20])
        # I2C_ISS_1.I2C_READ(0x00, 2)
        while 1:
            I2C_ISS_1.I2C_CURRENT_READ(2)
    else:
        if(0):
            I2C_ISS_2.I2C_READ(0x7F, 1)
            I2C_ISS_2.I2C_READ(0xEF, 1)
        if(1):
            I2C_ISS_2.I2C_CURRENT_READ(2)
        else:
            I2C_ISS_1.I2C_WRITE(0xEF, [0x09])
    '''
    I2C_ISS_1 = I2C_ISS('COM6', 1, 0xA0, 400)
    # I2C_ISS_1 = I2C_ISS('COM7', 1, 0x04, 100)
    # I2C_ISS_1.I2C_WRITE(0x00, [0x02])
    count = 0
    while(1):
        I2C_ISS_1.I2C_CURRENT_READ(1)
        count += 1
        print("count = %d" %count)
        if(count == 1000):
            break
    '''
    
    
    print("[End Script]: Interface.py")
    