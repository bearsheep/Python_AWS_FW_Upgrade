#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import struct
import argparse
import binascii

from intelhex import hex2bin

class VendorInfo(object):
    IMAGE_SECTION_MAP = {
        'READ': 0x01,
        'APP': 0x81,
        'TABLE_CMIS': 0x82,
        'TABLE_INTERNAL': 0x83,
        'DSP': 0x84,
        'BOOTLOADER': 0x85
    }

    def pack(self, file_size, file_crc32, firmware_version, build_version, firmware_type, offset_addr, module_number, vendor_pn):
        firmware_version = firmware_version.zfill(4)
        build_version = build_version.zfill(4)
        module_number = module_number.ljust(16, ' ')
        vendor_pn = vendor_pn.ljust(16, ' ')
        vendor_info = module_number.upper() + \
                      vendor_pn.upper() + \
                      struct.pack('B', 0x18) + \
                      struct.pack('B', 0x00) * (15) + \
                      struct.pack('>I', file_size) + \
                      struct.pack('>I', file_crc32) + \
                      struct.pack('>I', int(firmware_version[:2]) << 24 | int(firmware_version[2:4]) << 16 |
                                        int(build_version[:2]) << 8 | int(build_version[2:4])) + \
                      struct.pack('B', VendorInfo.IMAGE_SECTION_MAP[firmware_type])
        vendor_info += struct.pack('B', 0x00) * (112 - len(vendor_info))
        return vendor_info

def convert_file_format(filename, firmware_version='0100', build_version='6789', firmware_type='APP',
                        module_number='', vendor_pn='', start=None, end=None, size=None):
    """convert hexadecimal format to binary format"""
    (fname, ext) = os.path.splitext(filename)
    bin_file = fname + "_" + firmware_type + ".bin"
    with open(filename, 'rb' if ext == '.bin' else 'rt') as fin, open(bin_file, 'wb') as fout:
        if firmware_type.upper().startswith('DSP'):
            if ext == '.txt':
                convert_dsp_file_format(fin, fout)
            elif ext == '.bin':
                convert_binary_dsp_file(fin, fout)
        else:
            # hex2bin(fin, fout, start, end, size, pad=0xFF)
            hex2bin(fin, fout, start, end, size, pad=0x00)  # Change from 0xFF to 0x00 same as bootloader GUI, Lance 07/25/22.
    append_vendor_info(bin_file, firmware_version, build_version, firmware_type, start, module_number, vendor_pn)

def convert_dsp_file_format(fin, fout):
    result = ''
    total_bytes = 0
    for hexstr in fin.readlines():
        hexstr = hexstr.strip()

        if '//' in hexstr:
            continue

        for h in range(0, 4):
            b = int(hexstr[6 - h * 2:6 - h * 2 + 2], 16)
            # b = int(hexstr[h*2:h*2+2], 16)
            result += struct.pack('B', b)
        fout.write(result)
        total_bytes += len(result)
        result = ''

    # try to pad 0xFF
    padding = 256 - total_bytes % 256
    if 0 < padding < 256:
        fout.write(struct.pack('B', 0xFF) * padding)

def convert_binary_dsp_file(fin, fout):
    origin = fin.read()
    total_bytes = len(origin)
    fout.write(origin)

    # try to pad 0xFF
    padding = 256 - total_bytes % 256
    if 0 < padding < 256:
        fout.write(struct.pack('B', 0xFF) * padding)

def append_vendor_info(target_file, firmware_version, build_version, type, offset, module_number, vendor_pn):
    crc32_value = 0x00000000
    if not offset: offset = 0

    with open(target_file, 'rb+') as fout:
        data = fout.read()

        vendor_info = VendorInfo()
        fout.seek(0)
        # binascii.crc32 Final Xor Value = 0xFFFFFFFF
        # crc32_value = (binascii.crc32(data) & 0xFFFFFFFF)
        # Change Final Xor Value to 0x00000000 match 400G DR4 Bizlink module
        crc32_value = (binascii.crc32(data) & 0xFFFFFFFF) ^ 0xFFFFFFFF
        fout.write(vendor_info.pack(len(data), crc32_value, firmware_version,
                                    build_version, type, offset, module_number, vendor_pn))
        fout.write(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert hex file format to bin file format')

    parser.add_argument('file',
                        help='the hex file to be converted')
    parser.add_argument('-v', '--firmware-version', dest='firmware_version',
                        help='firmware version. e.g. 1005=v10.05', required=True)
    parser.add_argument('-b', '--builde-version', dest='build_version',
                        help='build version. e.g. 1005=v10.05', required=True)
    parser.add_argument('-t', '--type', dest='firmware_type',
                        choices=('APP', 'TABLE_CMIS', 'TABLE_INTERNAL', 'DSP', 'BOOTLOADER', 'READ'),
                        help='which firmware type to be upgraded.', required=True)
    parser.add_argument('-r', '--range', dest='range',
                        help='specify address range for writing output(hex value)\nRange can be in form "START:" or ":END".')
    parser.add_argument('-m', '--moudle-number', dest='module_number', help='module number', required=True)
    parser.add_argument('-n', '--vendor-pn', dest='vendor_pn', help='vendor pn', required=True)
    parser.add_argument('-s', '--size', dest='size',
                        help='size of output (decimal value).')

    args = parser.parse_args()

    start = None
    end = None
    size = None
    if args.range:
        l = args.range.split(":")
        if l[0] != '':
            start = int(l[0], 16)
        if l[1] != '':
            end = int(l[1], 16)
    if args.size:
        size = int(args.size, 10)

    convert_file_format(args.file, args.firmware_version, args.build_version,
                        args.firmware_type, args.module_number, args.vendor_pn, start, end, size)
