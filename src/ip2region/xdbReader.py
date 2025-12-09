# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# xdbReader.py
# Official ip2region v2.0+ Reader for Python
# Source: https://github.com/lionsoul2014/ip2region
# -------------------------------------------------------------------------------

import os
import mmap
import struct


class XdbReader(object):
    def __init__(self, dbpath):
        if not os.path.isfile(dbpath):
            raise Exception("xdb file not found: " + str(dbpath))

        self.f = open(dbpath, "rb")
        self.buf = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)

        self.header = self.buf[0:256]
        (self.first_index_ptr, self.last_index_ptr) = struct.unpack_from("<II", self.header, 0)

        self.index_count = (self.last_index_ptr - self.first_index_ptr) // 9 + 1

    def search(self, ip):
        ip = self.ip2long(ip)
        l = 0
        h = self.index_count - 1
        data_ptr = 0

        while l <= h:
            m = (l + h) >> 1
            p = self.first_index_ptr + m * 9
            sip, = struct.unpack_from("<I", self.buf, p)

            if ip < sip:
                h = m - 1
            else:
                eip, = struct.unpack_from("<I", self.buf, p + 4)
                if ip > eip:
                    l = m + 1
                else:
                    data_len = self.buf[p + 8]
                    data_ptr = struct.unpack_from("<I", self.buf, p + 4)[0]
                    break

        if data_ptr == 0:
            return "NOT FOUND"

        data_len = self.buf[p + 8]
        data_offset = data_ptr & 0x00FFFFFF
        return self.buf[data_offset:data_offset + data_len].decode("utf-8")

    @staticmethod
    def ip2long(ip):
        parts = ip.split(".")
        return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])

    def close(self):
        self.buf.close()
        self.f.close()
