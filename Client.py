import socket
import multiprocessing
import threading
import datetime
import time
import struct
import os
from Collector import Collector
import Constant

DATA_FOLDER = 'measured_data'
SLEEP_TIME = 0.01

class Client:
    def __init__(self, host, port, ch, bw):
        # get mac address of this device
        stream = os.popen('iw wlan0 info | grep addr')
        tmp = stream.read().split()
        self.mac_addr = tmp[1]

        # try to connect to the server
        self.flag_connected_to_server = False

        if host is not None:
            self.client_socket = socket.socket()
            print('Connecting to %s...' % host)
            try:
                self.client_socket.connect((host, port))
                msg_from_server = self.client_socket.recv(Constant.BUFFER_SIZE)
                print(msg_from_server.decode('UTF-8'))

                self.client_socket.send(str.encode(self.mac_addr))              # send mac address
                self.client_socket.send(str.encode(Constant.KEY_CSI_CLIENT))    # send key
                self.client_socket.recv(Constant.BUFFER_SIZE)
                self.flag_connected_to_server = True
            except socket.error as e:
                print(str(e))
                exit()
        
        # initiate CSI collector
        self.init_time = time.time()
        self.packet_queue = multiprocessing.Manager().Queue()   # queue
        self.count = 0

        self.collector = Collector(self.packet_queue, self.init_time)
        self.collector.set_channel(ch, bw)


    def run(self):
        if self.flag_connected_to_server:
            thread = threading.Thread(target=self.send_thread)
            thread.start()
            thread1 = threading.Thread(target=self.recv_thread)
            thread1.start()

            thread.join()
            # thread1.join()
        else:
            self.save_to_local()

    def send_thread(self):
        while True:
            if self.packet_queue.empty():
                time.sleep(SLEEP_TIME)
                continue

            (elapsed_time, pkt) = self.packet_queue.get()
            if elapsed_time < 0:
                self.client_socket.close()
                break

            self.count += 1
            elapsed_time_send = time.time() - self.init_time
            pkt_to_send = struct.pack('f', elapsed_time) + struct.pack('f', elapsed_time_send) + struct.pack('I', len(pkt)) + pkt
            self.client_socket.send(pkt_to_send)
            print('packet counter: %d, bytes: %d, remaining pkt: %d' % (self.count, len(pkt_to_send), self.packet_queue.qsize()), end='\r')
            # self.client_socket.recv(Constant.BUFFER_SIZE)

    def recv_thread(self):
        while True:
            pkt = self.client_socket.recv(Constant.BUFFER_SIZE)
            if len(pkt) == 0:
                break
            msg = pkt.decode('UTF-8').split(', ')
            if msg[0] == 'CMD_START_CSI' and len(msg) >= 3:
                ch = int(msg[1])
                bw = int(msg[2])
                self.collector.start(ch, bw)
            elif msg[0] == 'CMD_STOP_CSI':
                self.collector.stop()
            else:
                print('Unknown command: ' + msg[0])
       

    # def run_send_to_server(self):
    #     server_status_check_interval = 1
    #     last_status_check_time = time.time()
    #     next_pkt_to_send = None
    #     flag_quit = False

    #     while True:
    #         if time.time() - last_status_check_time > server_status_check_interval: 
    #             # check if server has new message
    #             last_status_check_time = time.time()
    #             self.client_socket.send(str.encode('CMD_STATUS'))
    #             pkt = self.client_socket.recv(Constant.BUFFER_SIZE)
    #             msg = pkt.decode('UTF-8').split(', ')
    #             print(msg)
    #             if msg[0] == 'CMD_START_CSI':
    #                 if len(msg) >= 3:
    #                     ch = int(msg[1])
    #                     bw = int(msg[2])
    #                     self.collector.start(ch, bw)
    #             elif msg[0] == 'CMD_STOP_CSI':
    #                 self.collector.stop()
    #             # self.client_socket.recv(Constant.BUFFER_SIZE)


    #         # prepare packet to send
    #         pkt_len_set = []
    #         pkt_to_send = b''
    #         if next_pkt_to_send is not None:
    #             pkt_len_set.append(len(next_pkt_to_send))
    #             pkt_to_send += next_pkt_to_send
    #             next_pkt_to_send = None
            
    #         while not self.packet_queue.empty():
    #             csi_dat = self.packet_queue.get()
    #             if csi_dat[0] < 0:                          # check quit flag
    #                 flag_quit = True
    #                 break
    #             curr_pkt_to_send = struct.pack('f', csi_dat[0]) + csi_dat[1]
    #             if len(pkt_to_send) + len(curr_pkt_to_send) >= Constant.BUFFER_SIZE:
    #                 next_pkt_to_send = curr_pkt_to_send     # this packet will be sent next turn
    #                 break
    #             else:
    #                 pkt_len_set.append(len(curr_pkt_to_send))
    #                 pkt_to_send += curr_pkt_to_send

    #         if flag_quit:
    #             self.client_socket.close()
    #             break

    #         if len(pkt_len_set) == 0:       # no packet to send
    #             time.sleep(SLEEP_TIME)
    #             continue

    #         # send packet
    #         self.comm_count += 1
    #         self.sent_pkt_count += len(pkt_len_set)

    #         elapsed_time_send = time.time() - self.init_time
    #         header = 'CMD_CSI_DATA, %f' % elapsed_time_send
    #         header += ', ' + ', '.join([str(x) for x in pkt_len_set])

    #         print('counter: %d, sending %d pkt (%d bytes), remaining pkt: %d' % (self.comm_count, len(pkt_len_set), len(pkt_to_send), self.packet_queue.qsize()), end='\r')
    #         # print(pkt_to_send)
    #         self.client_socket.send(str.encode(header))
    #         self.client_socket.recv(Constant.BUFFER_SIZE)
    #         self.client_socket.send(pkt_to_send)
    #         self.client_socket.recv(Constant.BUFFER_SIZE)
            
    
    def save_to_local(self):
        if not os.path.isdir(DATA_FOLDER):
            os.mkdir(DATA_FOLDER)
        now = datetime.datetime.now()
        filename = '%s/client_%s_%s.txt' % (DATA_FOLDER, self.mac_addr.replace(':', ''), now.strftime('%y%m%d_%H%M%S'))
        file = open(filename, 'w')

        while True:
            if self.packet_queue.empty():       # if queue is empty -> sleep
                time.sleep(SLEEP_TIME)
                continue

            elapsed_time, pkt = self.packet_queue.get()
            if elapsed_time < 0:      # quit flag
                break

            file.write('%f, %s\n' % (elapsed_time, pkt.hex()))
            file.flush()