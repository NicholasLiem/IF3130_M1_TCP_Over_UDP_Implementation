"""Codee for Server"""
import sys
import os
from lib.connection import Connection
from lib.segment import Segment


class Server:
    """Class to represent Server's side """
    def __init__(self,ip,port) -> None:
        self.ip = ip
        self.port = port
        self.conn = Connection(self.ip,self.port)

    def start_udp_server(self,filename):
        """Function to start UDP server"""
        self.conn.bind()
        print(f"[!] Server started at {self.ip}:{self.port}")
        print(f"[!] Source file | {filename} | {self.filesize(filename)} bytes")
        print(f"[!] Listening to broadcast address for clients.")

        # Initializing Client List
        # Send to the server would you like to listen to this client
        client_list = []
        try:
            while True:
                # First step: Server Receiving Connection Request (SYN from Client)
                syn_request, client_address = self.conn.recvfrom()
                if syn_request:
                    # Check the request has SYN flag
                    unpacked_segment = Segment()
                    unpacked_segment.unpack(syn_request)
                    if unpacked_segment.flags == Segment.SYN:
                        print(f"[!] Received request from {client_address[0]}:{client_address[1]}")
                        client_list.append((client_address, unpacked_segment.seq_num))
                    else:
                        print("[!] [Received-Request-Error] No SYN Segment Received")

                    # Continue Reading Conn after Three way Handshake finish
                    continue_listening = input("[?] Listen more? (y/n): ")
                    if continue_listening.lower() != 'y':
                        print("\nClient list:")
                        for i, client in enumerate(client_list, 1):
                            print(f"{i}. {client[0][0]}:{client[0][1]}")
                        break

            print(f"\n[!] Commencing file transfer...")
            for client_address, seq_num in client_list:
                self.perform_handshake(client_address, seq_num)
                self.perform_file_transfer(client_address, filename)

        except KeyboardInterrupt:
            print("\nServer is shutting down.")
        finally:
            self.conn.close()
            print("Server socket closed.")


    def perform_handshake(self,client_address, seq_num):
        """Function to start handshake"""
        syn_ack_segment = Segment(seq_num=0, ack_num=seq_num + 1, flags=(Segment.SYN | Segment.ACK))
        # Second step: Send a SYN + ACK here to the Client
        print(f"[!] [Handshake] (Sending SYN ACK) Handshake to client {client_address[0]}:{client_address[1]}....")
        self.conn.sendto(syn_ack_segment.pack(), client_address)

        expected_ack_num = seq_num + 1
        received = False

        # Third step: Waiting ACK from the Client
        while not received:
            ack_from_client, _ = self.conn.recvfrom()
            if ack_from_client:
                print(f"[!] [Handshake] (Received) Last ACK from {client_address[0]}:{client_address[1]}")
                unpacked_segment = Segment()
                unpacked_segment.unpack(ack_from_client)
                if unpacked_segment.flags == Segment.ACK and unpacked_segment.ack_num == expected_ack_num:
                    print(f"[!] [Handshake] (Completed) Handshake to client {client_address[0]}:{client_address[1]}")
                    return
                else:
                    print("[!] [Handshake-Error] Incorrect ACK Segment Received")


    def perform_file_transfer(self,client_address, filename, window_size=5):
        """Function to start performing file transfer"""
        try:
            with open(filename, 'rb') as file:
                sequence_base = 0
                sequence_num = 0
                file_segments = {}
                eof_reached = False
                last_ack_received =0
                sequence_max = sequence_base + window_size
                
                while True:
                    print(f"Debug: sequence_base={sequence_base}, sequence_max={sequence_max}, eof_reached={eof_reached}, sequence_number={sequence_num}")

                    while sequence_num <= sequence_max and not eof_reached:
                        data = file.read(Segment.MAX_SEGMENT_SIZE - 12)
                        if data:
                            print(f"[Client {client_address[0]}:{client_address[1]}] [Num={sequence_num}] Sending segment...")
                            segment = Segment(seq_num=sequence_num, data=data)
                            file_segments[sequence_num] = segment.pack()
                            self.conn.sendto(file_segments[sequence_num], client_address)
                            sequence_num += 1
                        else:
                            eof_reached = True
                            print("Debug: EOF reached.")

                    # Handle ACKs and adjust window
                    ack_data, _ = self.conn.recvfrom()
                    if ack_data:
                        ack_segment = Segment()
                        ack_segment.unpack(ack_data)
                        if ack_segment.flags & Segment.ACK:
                            if last_ack_received == ack_segment.ack_num & last_ack_received != 0:
                                print("Error....")
                                # Kalau terjadi permintaan buat dikirim ulang 
                                if eof_reached:
                                    sequence_num = last_ack_received+1
                                    try:
                                        while file_segments[sequence_num]:
                                            self.conn.sendto(file_segments[sequence_num],client_address)
                                            print("Sending segment number ", sequence_num)
                                            sequence_num += 1
                                    except:
                                        break
                                if sequence_num%5 == 0:
                                    sequence_max = sequence_num
                                else:
                                    sequence_max = (sequence_num//5 + 1)*5
                            else:
                                print(f"[Client {client_address[0]}:{client_address[1]}] [Num={ack_segment.ack_num}] ACK "
                                    f"Received")
                                sequence_base = max(sequence_base, ack_segment.ack_num + 1)
                                sequence_max = sequence_base + window_size
                                print(f"Debug: Updated sequence_base={sequence_base}")
                            last_ack_received = ack_segment.ack_num

                    if eof_reached and sequence_base >= sequence_num:
                        print("Debug: All segments sent and ACKed. Exiting loop.")
                        break

                # Sending the last FIN segment indicating file transfer complete
                fin_segment = Segment(seq_num=sequence_num, flags=Segment.FIN)
                self.conn.sendto(fin_segment.pack(), client_address)
                print("Debug: FIN segment sent.")
        except IOError as e:
            print(f"Error reading file {filename}: {e}")

    def filesize(self,filename):
        """Function to get size of a file"""
        return os.path.getsize(filename) if os.path.exists(filename) else -1


if __name__ == "__main__":
    DEFAULT_IP_ADDRESS = "127.0.0.1"

    if len(sys.argv) != 3:
        print("Format: python server.py <port> <filename>")
        sys.exit(1)

    try:
        PORT = int(sys.argv[1])
    except ValueError:
        print("Error: Port number must be an integer.")
        sys.exit(1)

    FILENAME = sys.argv[2]
    server = Server(DEFAULT_IP_ADDRESS,PORT)
    server.start_udp_server(FILENAME)
