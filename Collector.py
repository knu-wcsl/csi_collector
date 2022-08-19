import multiprocessing
import os
from scapy.all import *

class Collector(multiprocessing.Process):       # create instance running on seperate process
    def __init__(self, packet_queue, init_time):
        multiprocessing.Process.__init__(self)
        self.init_time = init_time
        self.queue = packet_queue
        self.configure_monitor_mode()


    def __del__(self):
        os.system('ip link set mon0 down')


    def configure_monitor_mode(self):
        if not os.path.isdir('/sys/class/net/mon0'):
            os.system('ifconfig wlan0 up')
            os.system('iw dev wlan0 interface add mon0 type monitor')
        os.system('ip link set mon0 down')
        

    def set_channel(self, ch, bw):
        stream = os.popen('mcp -C %d -N %d -c %d/%d' % (1, 1, ch, bw))
        csi_param = stream.read()
        csi_param = csi_param[:-1]  # remove newline char
        os.system('nexutil -Iwlan0 -s500 -b -l34 -v%s' % csi_param)

    
    def run(self):
        # Overloaded function provided by multiprocessing.Process. Called upon start() signal
        os.system('ip link set mon0 up')
        self.counter = 0
        sniff(filter='udp port 5500', iface='wlan0', prn = self.process_packet, count = 0, store = 0)
        

    def process_packet(self, packet):
        self.counter += 1
        elapsed_time = time.time() - self.init_time

        print('counter: %d, elapsed_time: %f s' % (self.counter, elapsed_time))
        self.queue.put((elapsed_time, bytes(packet['UDP'].payload)))
