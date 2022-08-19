from multiprocessing.sharedctypes import Value
import socket
import multiprocessing
import datetime
import time
import struct
import os
from Collector import Collector

KEY_CSI_CLIENT = 'clkj209cjE!4k2GV#w02'
BUFFER_SIZE = 2048
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
            self.client_socket.settimeout(10)
            print('Connecting to %s...' % host)
            try:
                self.client_socket.connect((host, port))
                msg_from_server = self.client_socket.recv(BUFFER_SIZE)
                print(msg_from_server)

                self.client_socket.send(str.encode(self.mac_addr))      # send mac address
                self.client_socket.send(str.encode(KEY_CSI_CLIENT))     # send key
                self.client_socket.recv(BUFFER_SIZE)
                self.flag_connected_to_server = True
            except socket.error as e:
                print(str(e))
                exit()
        
        # initiate CSI collector
        self.init_time = time.time()
        self.packet_queue = multiprocessing.Manager().Queue()   # queue
        self.count = 0

        collector = Collector(self.packet_queue, self.init_time)
        collector.set_channel(ch, bw)
        collector.start()


    def run(self):
        if not self.flag_connected_to_server:   # save CSI to local device
            if not os.path.isdir('measured_data'):
                os.mkdir('measured_data')
            now = datetime.datetime.now()
            filename = 'measured_data/client_%s_%s.txt' % (self.mac_addr.replace(':', ''), now.strftime('%y%m%d_%H%M%S'))
            file = open(filename, 'w')
            
        while True:
            if self.packet_queue.empty():       # if queue is empty -> sleep
                time.sleep(SLEEP_TIME)
                continue

            (elapsed_time, pkt) = self.packet_queue.get()
            if elapsed_time < 0:                # stop
                if self.flag_connected_to_server:
                    self.client_socket.close()
                else:
                    file.close()
                break

            self.count += 1
            elapsed_time_send = time.time() - self.init_time

            if self.flag_connected_to_server:   # send results to server
                pkt_to_send = struct.pack('f', elapsed_time) + struct.pack('f', elapsed_time_send) + struct.pack('I', len(pkt)) + pkt
                self.client_socket.send(pkt_to_send)
                print('sending packet (%d bytes), remaining: %d' % (len(pkt_to_send), self.packet_queue.qsize()))
            else:                               # write results to the local file
                file.write('%f, %s\n' % (elapsed_time, pkt.hex()))
                file.flush()