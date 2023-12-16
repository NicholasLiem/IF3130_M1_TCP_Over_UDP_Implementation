import socket
from lib.segment import Segment


# Wrapper class buat UDP Connection
class Connection:
    # BUFFER SIZE (2^16)
    BUFFER_SIZE = 65536

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(30)

    # Binding ip and port to this conn
    def bind(self):
        self.socket.bind((self.ip, self.port))

    # Buat ngirim datagram ngengg
    def sendto(self, message, addr):
        self.socket.sendto(message, addr)

    # Socket masuknya datagram
    def recvfrom(self, buffer_size=BUFFER_SIZE):
        try:
            segment, addr = self.socket.recvfrom(buffer_size)
            return segment, addr
        except socket.timeout:
            print("Socket timed out")
            return None, None

    def send_syn_segment(self, addr):
        syn_segment = Segment(seq_num=0, ack_num=0, flags=Segment.SYN)
        packed_segment = syn_segment.pack()
        self.sendto(packed_segment, addr)

    def send_ack_segment(self, addr, ack_num):
        ack_segment = Segment(seq_num=0, ack_num=ack_num, flags=Segment.ACK)
        packed_segment = ack_segment.pack()
        self.sendto(packed_segment, addr)

    # Jelas lah ya buat nutup koneksi
    def close(self):
        self.socket.close()
