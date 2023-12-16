import struct
from lib.util import crc16


class Segment:
    # MAX Segment Size
    MAX_SEGMENT_SIZE = 32768
    
    HEADER_SIZE = 12
    DATA_SIZE = MAX_SEGMENT_SIZE - HEADER_SIZE
    
    # FLAGS
    SYN = 0x02
    ACK = 0x10
    FIN = 0x01

    # SEGMENT TYPE
    FILEDATA = 0x01
    METADATA = 0x02

    def __init__(self, seq_num=0, ack_num=0, flags=0, segment_type=0, checksum=0, data=b''):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.segment_type = segment_type
        self.checksum = checksum
        self.data = data

    # Penjelasan "!LLHH": ! itu untuk menunjukkan kalau dia big endian (byte order)
    # L buat unsigned long (4 bytes for seq num and ack num)
    # H buat unsigned short (2 byes for flags and check sum)
    # Jadi kalo dicompile jadinya 4 byte for sq num, 4 byte for ack nm, 2 byte for flag, 2 byte for checksum
    def pack(self):
        self.checksum = self.calculate_checksum()
        header = struct.pack('!LLBBH', self.seq_num, self.ack_num, self.flags, self.segment_type, self.checksum)
        return header + self.data

    # Total byte dari header adalah 12, jadi kita mulai pembacaan dari 12 byte ke atas
    def unpack(self, segment):
        header = segment[:Segment.HEADER_SIZE]
        self.seq_num, self.ack_num, self.flags, self.segment_type, self.checksum = struct.unpack('!LLBBH', header)
        self.data = segment[Segment.HEADER_SIZE:]

    def calculate_checksum(self):
        s = struct.pack('!LLBB', self.seq_num, self.ack_num, self.flags, self.segment_type) + self.data
        return crc16(s)

    def validate_checksum(self):
        return self.calculate_checksum() == self.checksum

    def __str__(self):
        return (f'SeqNum: {self.seq_num}, AckNum: {self.ack_num}, Flags: {self.flags}, Checksum: {self.checksum}, Data '
                f'Length: {len(self.data)}')
