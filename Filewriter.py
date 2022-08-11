import multiprocessing
import datetime
import time
import struct
import os

SLEEP_TIME = 0.1
DATA_FOLDER = 'measured_data'

class Filewriter(multiprocessing.Process):
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self.queue = queue
        now = datetime.datetime.now()           # get current date and time
        if not os.path.isdir(DATA_FOLDER):
            os.mkdir(DATA_FOLDER)
        filename = DATA_FOLDER + '/' + now.strftime('server_%y%m%d_%H%M%S.txt')
        self.file = open(filename, 'w')         # create file
    

    def run(self):
        flag_req_flush = False
        while True:                             # run a loop
            if self.queue.empty():              # check if queue is empty or not
                if flag_req_flush:
                    self.file.flush()
                    flag_req_flush = False
                else:
                    time.sleep(SLEEP_TIME)
                continue
            
            (elapsed_time, name, pkt) = self.queue.get()
            if elapsed_time < 0:
                self.file.close()
                print('file writing stopped')
                break

            if len(pkt) < 12:
                continue
            t1 = struct.unpack('f', pkt[0:4])[0]
            t2 = struct.unpack('f', pkt[4:8])[0]
            n = struct.unpack('I', pkt[8:12])[0]
            
            if len(pkt) == n + 12:
                self.file.write('%f, %f, %f, %s, %s\n' % (elapsed_time, t1, t2, name, pkt[12:].hex()))   
                flag_req_flush = True    