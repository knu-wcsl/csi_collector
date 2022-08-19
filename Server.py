from pickle import TRUE
from socket import AF_INET, SOCK_STREAM
import socket
import time
import threading
import multiprocessing
from Filewriter import Filewriter

TYPE_CSI_CLIENT = 0
TYPE_FILE_TRANSFER_CLIENT = 1
KEY_CSI_CLIENT = 'clkj209cjE!4k2GV#w02'
KEY_FILE_TRANSFER_CLIENT = '#N2nb023flkn3lkj%!df'

BUFFER_SIZE = 2048
SLEEP_TIME = 0.1
FILE_CLOSE_TIME = 3600              # close file when the sever is idle for this amount of time

client_timeout = 10                 # close connection if client is inactive for this time[s]

class Server:
    def __init__(self, host, port):
        self.client_counter = 0             # number of active clients
        self.client_list = []               # list of clients
        self.host = host
        self.port = port

        self.server_socket = socket.socket(AF_INET, SOCK_STREAM)
        try:
            self.server_socket.bind((host, port))   # open server socket
        except socket.error as e:
            print(str(e))
            raise Exception('Server is not ready !')


    def __del__(self):                          # called when Ctrl+Z keys are pressed
        self.flag_server_is_running = False
    

    def run(self):                              # listen socket and accept new clients
        self.flag_server_is_running = True
        self.flag_file_opened = False           # file is not yet opened
        self.idle_time = 0

        thread = threading.Thread(target = self.server_status_check_routine)
        thread.start()

        self.server_socket.listen()
        print('Server is listening on the port %d' % self.port)
        while True:
            self.accept_connection()


    def accept_connection(self):                # accept new connection
        connection, addr = self.server_socket.accept()

        # Classify client type
        connection.send(str.encode('You are connected to %s:%d' % (self.host, self.port)))
        mac_addr = connection.recv(BUFFER_SIZE).decode('UTF-8')         # when connected, clients are supposed to send their mac addresses and keys depending on their purposes
        connection.send(str.encode('Received'))
        received_key = connection.recv(BUFFER_SIZE).decode('UTF-8')

        if received_key == KEY_CSI_CLIENT:
            if not self.flag_file_opened:                               # open a file to write CSI data
                self.packet_queue = multiprocessing.Manager().Queue()
                self.init_time = time.time()
                self.filewriter = Filewriter(self.packet_queue)         # create new file
                self.filewriter.start()
                self.flag_file_opened = True

            self.client_counter += 1
            client = ConnectedClient(TYPE_CSI_CLIENT, mac_addr, self.client_counter, connection, addr, self.init_time, self.packet_queue, self.close_connection, None)
            self.client_list.append(client)


        elif received_key == KEY_FILE_TRANSFER_CLIENT:
            self.client_counter += 1
            client = ConnectedClient(TYPE_FILE_TRANSFER_CLIENT, self.client_counter, connection, addr, self.init_time, self.packet_queue, self.close_connection, self.get_server_status)
            self.client_list.append(client)

        else:
            print('Unidentified key')
            connection.close()


    def server_status_check_routine(self):
        check_interval = 10                         # run every 10 secs
        idle_time = 0
        while True:
            if not self.flag_server_is_running:     # Ctrl+Z
                break   

            if self.flag_file_opened:               # check if there are CSI clients and keep the file opened
                flag_exist_csi_client = False
                for client in self.client_list:
                    if client.type == TYPE_CSI_CLIENT:
                        flag_exist_csi_client = True
                        break
                
                if flag_exist_csi_client:           # keep the file opened
                    idle_time = 0
                else:
                    idle_time += check_interval

                if idle_time > FILE_CLOSE_TIME:     # timeout -> close the opened file
                    self.packet_queue.put(-1, None, None)
                    self.flag_file_opened = False
            time.sleep(check_interval)
    

    def close_connection(self, num):        # remove client which number is 'num'
        for i in range(len(self.client_list)):
            if self.client_list[i].num == num:
                self.client_list.pop(i)
                break

    def get_server_status(self):
        return 'A'

class ConnectedClient:
    def __init__(self, client_type, mac_addr, num, connection, addr, init_time, packet_queue, close_callback, server_status):
        self.type = client_type
        self.name = mac_addr
        self.num = num
        self.connection = connection
        self.ip = addr[0]
        self.port = addr[1]
        self.init_time = init_time
        self.packet_queue = packet_queue
        self.close_callback = close_callback
        self.server_status_callback = server_status
        self.packet_counter = 0

        thread = threading.Thread(target = self.message_exchange_thread)
        thread.start()

    def message_exchange_thread(self):
        if self.type == TYPE_CSI_CLIENT:    # keep receiving CSI data from client and put them to the queue
            while True:
                pkt = self.connection.recv(BUFFER_SIZE)
                if len(pkt) == 0:
                    print('CSI client %s is disconnected' % self.name)
                    break

                self.packet_counter += 1
                elapsed_time = time.time() - self.init_time
                print('%.2fs: packet num: %d (%d bytes) from %s (%s)' % (elapsed_time, self.packet_counter, len(pkt), self.name, self.ip))
                self.packet_queue.put((elapsed_time, self.name, pkt))

        # close connection
        self.connection.close()
        self.close_callback(self.num)