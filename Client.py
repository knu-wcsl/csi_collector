import socket
import multiprocessing
import datetime
import time
import struct
import os
from Collector import Collector
import Constant
import copy

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
                print(msg_from_server)

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
        self.comm_count = 0
        self.sent_pkt_count = 0

        self.collector = Collector(self.packet_queue, self.init_time)
        self.collector.set_channel(ch, bw)


    def run(self):
        if self.flag_connected_to_server:
            self.run_send_to_server()
        else:
            self.run_save_to_local()
    
    def run_send_to_server(self):
        server_status_check_interval = 1
        last_status_check_time = time.time()
        next_pkt_to_send = None
        flag_quit = False

        while True:
            if time.time() - last_status_check_time > server_status_check_interval: 
                # check if server has new message
                last_status_check_time = time.time
                self.client_socket.send(str.encode('CMD_STATUS'))
                pkt = self.client_socket.recv(Constant.BUFFER_SIZE)
                msg = pkt.decode('UTF-8').split(', ')
                if msg[0] == 'CMD_START_CSI':
                    if len(msg) >= 3:
                        ch = int(msg[1])
                        bw = int(msg[2])
                        self.collector.start(ch, bw)
                elif msg[0] == 'CMD_STOP_CSI':
                    self.collector.stop()

            # prepare packet to send
            pkt_len_set = []
            pkt_to_send = b''
            if next_pkt_to_send is not None:
                pkt_len_set.append(len(next_pkt_to_send))
                pkt_to_send += next_pkt_to_send
                next_pkt_to_send = None
            
            while not self.packet_queue.empty():
                csi_dat = self.packet_queue.get()
                if csi_dat[0] < 0:                          # check quit flag
                    flag_quit = True
                    break
                curr_pkt_to_send = struct('f', csi_dat[0]) + csi_dat[1]
                if len(pkt_to_send) + len(curr_pkt_to_send) >= Constant.BUFFER_SIZE:
                    next_pkt_to_send = curr_pkt_to_send     # this packet will be sent next turn
                    break
                else:
                    pkt_len_set.append(len(curr_pkt_to_send))
                    pkt_to_send += curr_pkt_to_send

            if flag_quit:
                self.client_socket.close()
                break

            if len(pkt_len_set) == 0:       # no packet to send
                time.sleep(SLEEP_TIME)
                continue

            # send packet
            self.comm_count += 1
            self.sent_pkt_count += len(pkt_len_set)

            elapsed_time_send = time.time() - self.init_time
            header = 'CMD_CSI_DATA, %f' % elapsed_time_send + pkt_len_set.join
            header += ', ' + ', '.join([str(x) for x in pkt_len_set])

            self.client_socket.send(str.encode(header))
            self.client_socket.send(pkt_to_send)
            print('sent %d pkt (%d bytes), remaining pkt: %d' % (len(pkt_len_set), len(pkt_to_send), self.packet_queue.qsize()))
            
    
    def run_save_to_local(self):
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