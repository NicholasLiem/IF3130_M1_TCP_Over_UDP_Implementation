import os
import sys
from lib.connection import Connection
from lib.segment import Segment


class Client:
    """Class to represent Client side"""
    def __init__(self,port,server_ip,server_port) -> None:
        self.client_port = port
        self.server_ip = server_ip
        self.server_port = server_port
        self.conn = Connection(self.server_ip,self.client_port)

    def receive_udp_message(self, path_output):
        """Function used to receive udp message"""
        self.conn.bind()
        print(f"[!] Client started at {self.server_ip}:{self.client_port}")

        print(f"[!] [Handshake] (Sending) Broadcast SYN Request to port {self.server_port}")
        # Initiating handshake... SENDING SYN
        self.conn.send_syn_segment((self.server_ip, self.server_port))

        print(f"[!] [Handshake] Waiting for response...")
        # Waiting for SYN-ACK from Server
        syn_ack_from_server, _ = self.conn.recvfrom()
        # When received kita lakukan unpacking segmentnya, buat ack_numnya dan send the server
        if syn_ack_from_server:
            print(f"[!] [Handshake] (Received) SYN ACK from server")
            syn_ack_segment = Segment()
            syn_ack_segment.unpack(syn_ack_from_server)
            if syn_ack_segment.flags == (Segment.SYN | Segment.ACK):
                ack_num = syn_ack_segment.seq_num + 1
                print(f"[!] [Handshake] (Sending) Last ACK to server")
                self.conn.send_ack_segment((self.server_ip, self.server_port), ack_num)
            else:
                # Implement retry
                print(f"[!] [Handshake-Error] SYN ACK from server is not valid.")

        self.receive_file(path_output)

        # Close the socket
        self.conn.close()
        print("[!] Connection closed.")

    def _process_output_path(self, path_output, filename):
        if path_output == "." or path_output == ".." or os.path.isdir(path_output):
            return os.path.join(path_output, filename)
        else:
            return path_output

    def receive_file(self,path_output):
        """Function to receive file"""
        expected_seq_num = 0
        last_seq_num = 0
        # get file metadata
        while True:
            segment_data, _ = self.conn.recvfrom()
            if not segment_data:
                print("[!] No data received. Ending file reception.")
                break
            segment = Segment()
            segment.unpack(segment_data)
            valid = segment.validate_checksum()
            if segment.seq_num == expected_seq_num and valid:
                if segment.segment_type == Segment.METADATA:
                    path_output = self._process_output_path(path_output, segment.data.strip(b"\0").decode())
                    self.send_ack(expected_seq_num)
                    last_seq_num = expected_seq_num
                    expected_seq_num += 1
                    break
            elif not valid:
                print(f"[!] Corrupted checksum in segment {expected_seq_num}.")
                self.send_ack(last_seq_num)
            else:
                print(f"[!] Missed segment {expected_seq_num}.")
                self.send_ack(last_seq_num)
        with open(path_output, 'wb') as file:
            while True:
                segment_data, _ = self.conn.recvfrom()
                if not segment_data:
                    print("[!] No data received. Ending file reception.")
                    break

                segment = Segment()
                segment.unpack(segment_data)
                valid = segment.validate_checksum()
                if segment.seq_num == expected_seq_num and valid:
                    if segment.flags & Segment.FIN:
                        print(f"[!] Received FIN in segment {segment.seq_num}.")
                        self.send_fin_ack(expected_seq_num+1)
                        print("[!] End of file transmission. Closing connection.")
                        break

                    #marker = f"\n===== SEGMENT MARK, NUM = {segment.seq_num} =====\n"
                    file.write(segment.data)
                    print("[!] Writing data to file.")
                    self.send_ack(expected_seq_num)
                    last_seq_num = expected_seq_num
                    expected_seq_num += 1
                elif not valid:
                    print(f"[!] Corrupted checksum in segment {expected_seq_num}.")
                    self.send_ack(last_seq_num)
                else:
                    print(segment.segment_type)
                    print(f"[!] Missed segment {expected_seq_num}.")
                    self.send_ack(last_seq_num)
            return


    def send_ack(self,ack_num):
        """Function used to send ACK"""
        ack_segment = Segment(ack_num=ack_num, flags=Segment.ACK)
        self.conn.sendto(ack_segment.pack(), (self.server_ip, self.server_port))
        print(f"[!] Sending ACK for segment {ack_num}.")

    def send_fin_ack(self,ack_num):
        """Function used to send FIN ACK"""
        ack_segment = Segment(ack_num=ack_num, flags=Segment.FIN|Segment.ACK)
        self.conn.sendto(ack_segment.pack(), (self.server_ip, self.server_port))
        print(f"[!] Sending FIN ACK for segment {ack_num}.")

if __name__ == "__main__":
    DEFAULT_IP_ADDRESS = "127.0.0.1"

    if len(sys.argv) != 4:
        print("Format: python client.py <client port> [broadcast port] [path output]")
        sys.exit(1)

    try:
        CLIENT_PORT = int(sys.argv[1])
        BROADCAST_PORT = int(sys.argv[2])
    except ValueError:
        print("Error: Port number must be an integer.")
        sys.exit(1)

    PATH_OUTPUT = sys.argv[3]
    client = Client(CLIENT_PORT,DEFAULT_IP_ADDRESS,BROADCAST_PORT)
    client.receive_udp_message(PATH_OUTPUT)
