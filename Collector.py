import multiprocessing
import os
from scapy.all import *


class Collector:        # create instance running on seperate process

    def __init__(self, packet_queue, init_time):
        self.curr_ch = None
        self.curr_bw = None
        self.configure_monitor_mode()
        packetListener = PacketListener(packet_queue, init_time)
        packetListener.start()

    def __del__(self):
        self.stop()

    def configure_monitor_mode(self):
        if not os.path.isdir('/sys/class/net/mon0'):
            os.system('iw dev wlan0 interface add mon0 type monitor')
            os.system('ifconfig wlan0 up')
        self.stop()
        
    def set_channel(self, ch, bw):
        if self.curr_ch != ch or self.curr_bw != bw:
            print('Monitoring channel: %d, bandwidth: %d' % (ch, bw))
            self.curr_ch = ch
            self.curr_bw = bw
            stream = os.popen('mcp -C %d -N %d -c %d/%d' % (1, 1, ch, bw))
            csi_param = stream.read()
            csi_param = csi_param[:-1]  # remove newline char
            os.system('nexutil -Iwlan0 -s500 -b -l34 -v%s' % csi_param)
    
    def start(self, ch, bw):
        print('monitoring mode up')
        os.system('ip link set mon0 up')
        self.set_channel(ch, bw)

    def stop(self):
        print('monitoring mode down')
        # os.system('iw dev mon0 del')
        os.system('ip link set mon0 down')



class PacketListener(multiprocessing.Process):
    def __init__(self, queue, init_time):
        multiprocessing.Process.__init__(self)
        self.init_time = init_time
        self.queue = queue
        self.counter = 0

    def __del__(self):
        self.queue.put((-1, None))  # stop writing file

    def run(self):
        print('Listening UDP packets on port 5500')
        sniff(filter='udp port 5500', iface='wlan0', prn=self.process_packet, count=0, store=0)

    def process_packet(self, packet):
        self.counter += 1
        elapsed_time = time.time() - self.init_time
        self.queue.put((elapsed_time, bytes(packet['UDP'].payload)))