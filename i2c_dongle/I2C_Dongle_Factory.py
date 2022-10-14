class I2C_Dongle_Factory(object):

    @staticmethod
    def create_dongle_object(dongle):
        if dongle == 'CH341':
            from I2C_Dongle_CH341 import I2C_Dongle_CH341
            return I2C_Dongle_CH341
        elif dongle == 'USB-ISS':
            try:
                from I2C_Dongle_USB_ISS import I2C_Dongle_USBISS
                return I2C_Dongle_USBISS
            except ImportError:
                raise ImportError('Unable to find usb-iss python package! Install via \'pip install usb-iss\'')
        elif dongle == 'SMBUS':
            try:
                from I2C_SMBUS import I2CSMBUS
                return I2CSMBUS
            except ImportError:
                raise ImportError('Unable to find SMBUS python package! Install via \'pip install smbus2\'')
        elif dongle == 'SMBUS_EOS':
            try:
                from I2C_SMBUS_EOS import I2CSMBUS_EOS
                return I2CSMBUS_EOS
            except ImportError:
                raise ImportError('Unable to find SMBUS_EOS python package!')
        else:
            from I2C_Dongle_Aardvark import I2C_Dongle_Aardvark
            return I2C_Dongle_Aardvark

    @staticmethod
    def get_dongles():
        return ['AARDVARK', 'CH341', 'USB-ISS', 'SMBUS', 'SMBUS_EOS']

    @staticmethod
    def add_dongle_arguments(parser):
        parser.add_argument(
            '-d', '--dongle',
            dest='dongle',
            help='the usage of communication interface.',
            choices=I2C_Dongle_Factory.get_dongles()
        )
        parser.add_argument(
            '-p', '--port',
            dest='port',
            help='the port number which i2c dongle device is attached.'
        )
