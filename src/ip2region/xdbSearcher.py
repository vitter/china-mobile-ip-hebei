# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# xdbSearcher.py
# Official ip2region v2.0+ Searcher for Python
# Source: https://github.com/lionsoul2014/ip2region
# -------------------------------------------------------------------------------

import struct


class XdbSearcher:
    def __init__(self, vIndex, vData):
        self.vIndex = vIndex
        self.vData = vData

        # index header: first index ptr / last index ptr
        self.first_index_ptr, self.last_index_ptr = struct.unpack_from("<II", self.vIndex, 0)
        self.index_count = (self.last_index_ptr - self.first_index_ptr) // 9 + 1

    @staticmethod
    def load_index(dbpath):
        with open(dbpath, "rb") as f:
            header = f.read(256)
            first_index_ptr, last_index_ptr = struct.unpack_from("<II", header, 0)
            index_len = last_index_ptr + 9 - 256

            f.seek(0)
            return f.read(256 + index_len)

    @staticmethod
    def load_data(dbpath):
        with open(dbpath, "rb") as f:
            return f.read()

    @staticmethod
    def ip2long(ip):
        parts = ip.split(".")
        return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])

    def search(self, ip):
        ip = self.ip2long(ip)
        l = 0
        h = self.index_count - 1
        data_ptr = 0
        data_len = 0
        p = 0

        while l <= h:
            m = (l + h) >> 1
            p = self.first_index_ptr + m * 9

            sip, = struct.unpack_from("<I", self.vIndex, p)
            if ip < sip:
                h = m - 1
            else:
                eip, = struct.unpack_from("<I", self.vIndex, p + 4)
                if ip > eip:
                    l = m + 1
                else:
                    data_len = self.vIndex[p + 8]
                    data_ptr = struct.unpack_from("<I", self.vIndex, p + 4)[0]
                    break

        if data_ptr == 0:
            return "NOT FOUND"

        data_offset = data_ptr & 0x00FFFFFF
        return self.vData[data_offset:data_offset + data_len].decode("utf-8")
