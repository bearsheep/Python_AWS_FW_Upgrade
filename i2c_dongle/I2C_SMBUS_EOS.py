from i2c_dongle.I2C_Dongle import I2C_Dongle
# noinspection PyUnresolvedReferences
import SmbusUtil


class I2CSMBUS_EOS(I2C_Dongle):
    def __init__(self, path):
        path = path[1:].split('/')
        if len(path) != 4 or path[0] != 'scd':
            raise ValueError("Device path error: should be /scd/<accelId>/<busId>/<deviceId>")

        self.accelId = int(path[1])
        self.busId = int(path[2])
        # self.deviceId = int(path[3],16)
        self.smbus_factory = SmbusUtil.Factory()

    def write(self, slave_addr, reg_addr, data, **kwargs):
        """
            Write data to i2c device.
            return zero if success, and non-zero if failed.
        """
        assert len(data) <= 256, 'max length of data should less than 256.'

        try:
            data = map(chr, data)
            slave_addr >>= 1

            if reg_addr is None:
                reg_addr = data[0]
                data = data[1:]

            device = self.smbus_factory.device(self.accelId, self.busId, slave_addr, 1,
                                               readDelayMs='delay10ms', writeDelayMs='delay10ms',
                                               busTimeout='busTimeout1000ms')

            device.write(reg_addr, data, max(1, len(data)))
            return 0
        except:
            return -1

    def read(self, slave_addr, reg_addr, num_bytes, **kwargs):
        """
            Read data from i2c device.
            return tuple (length, data), where data is a List object and
            length is an integer.
        """
        try:
            slave_addr >>= 1

            write_no_stop = False
            
            if reg_addr is None:
                reg_addr = kwargs['cmd']
                write_no_stop = True

            device = self.smbus_factory.device(self.accelId, self.busId, slave_addr, 1,
                                               readDelayMs='delay10ms', writeDelayMs='delay10ms',
                                               busTimeout='busTimeout1000ms', writeNoStopReadCurrent=write_no_stop)

            data_in = device.read(reg_addr, num_bytes, num_bytes)
            return len(data_in), data_in
        except:
            return 0, []

    def open_device(self, bitrate=100):
        """open i2c device"""
        pass

    def close_device(self):
        pass
