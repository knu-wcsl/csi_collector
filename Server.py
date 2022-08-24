from socket import AF_INET, SOCK_STREAM
import socket
import time
import threading
import multiprocessing
from Filewriter import Filewriter
import Constant

class Server:
    def __init__(self, host, port):
        self.client_counter = 0             # number of active clients
        self.client_list = []               # list of clients
        self.master_android_client = None   # only master control CSI start/stop

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
        mac_addr = connection.recv(Constant.BUFFER_SIZE).decode('UTF-8')         # when connected, clients are supposed to send their mac addresses and keys depending on their purposes
        received_key = connection.recv(Constant.BUFFER_SIZE).decode('UTF-8')
        connection.send(str.encode('Received'))

        if received_key == Constant.KEY_CSI_CLIENT:
            print('connected new csi client')
            if not self.flag_file_opened:                               # open a file to write CSI data
                self.packet_queue = multiprocessing.Manager().Queue()
                self.init_time = time.time()
                self.filewriter = Filewriter(self.packet_queue)         # create new file
                self.filewriter.start()
                self.flag_file_opened = True

            self.client_counter += 1
            client = ConnectedClient(Constant.TYPE_CSI_CLIENT, mac_addr, self.client_counter, connection, addr, self.callback_fun, init_time=self.init_time, packet_queue=self.packet_queue)
            self.client_list.append(client)


        elif received_key == Constant.KEY_FILE_TRANSFER_CLIENT:
            print('connected new file transfer client')
            self.client_counter += 1
            client = ConnectedClient(Constant.TYPE_FILE_TRANSFER_CLIENT, mac_addr, self.client_counter, connection, addr, self.callback_fun)
            self.client_list.append(client)


        elif received_key == Constant.KEY_ANDROID_CLIENT:
            self.client_counter += 1
            client = ConnectedClient(Constant.TYPE_ANDROID_CLIENT, mac_addr, self.client_counter, connection, addr, self.callback_fun)
            self.client_list.append(client)
            if self.master_android_client == None:
                self.master_android_client = self.client_counter
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
                    if client.type == Constant.TYPE_CSI_CLIENT:
                        flag_exist_csi_client = True
                        break
                
                if flag_exist_csi_client:           # keep the file opened
                    idle_time = 0
                else:
                    idle_time += check_interval

                if idle_time > Constant.FILE_CLOSE_TIME:        # timeout -> close the opened file
                    self.packet_queue.put(-1, None, None)
                    self.flag_file_opened = False
            time.sleep(check_interval)


    def callback_fun(self, events):
        event_type = events[0]
        if event_type == Constant.EVENT_CLOSE_CONNECTION:       # remove client
            client_num = events[1]
            for i in range(len(self.client_list)):
                if self.client_list[i].num == client_num:
                    self.client_list.pop(i)
                    break
            if client_num == self.master_android_client:
                # find new master client
                self.master_android_client = None
                for client in self.client_list:
                    if client.type == Constant.TYPE_ANDROID_CLIENT:
                        self.master_android_client = client.num
                        break

        elif event_type == Constant.EVENT_SERVER_STATUS:
            return self.get_server_status()

        elif event_type in [Constant.EVENT_START_CSI, Constant.EVENT_STOP_CSI]:     # start/stop CSI collection
            # check if client is master client
            client_num = events[-1]
            if client_num != self.master_android_client:
                return 'You are not master client'
            
            for client in self.client_list:
                count = 0
                if client.type == Constant.TYPE_CSI_CLIENT:
                    client.add_cmd(events)
                    count += 1
            return 'Sent CSI command to %d devices' % count


    def get_server_status(self):
        n_csi_client = 0
        n_status_check_client = 0
        n_file_transfer_client = 0

        csi_client_status = 'CSI client list:\n'
        for client in self.client_list:
            if client.type == Constant.TYPE_CSI_CLIENT:
                n_csi_client += 1
                csi_client_status += '%s: transferred %d packets\n' % (client.name, client.packet_counter)
            elif client.type == Constant.TYPE_FILE_TRANSFER_CLIENT:
                n_file_transfer_client += 1
            elif client.type == Constant.TYPE_ANDROID_CLIENT:
                n_status_check_client += 1

        status = '%d csi, %d file transfer, %d status check clients\n' % (n_csi_client, n_file_transfer_client, n_status_check_client)
        status += csi_client_status

        return status
            


class ConnectedClient:
    def __init__(self, client_type, mac_addr, num, connection, addr, server_callback,
                    init_time = None, packet_queue = None):
        self.type = client_type
        self.name = mac_addr
        self.num = num
        self.connection = connection
        self.ip = addr[0]
        self.port = addr[1]
        self.init_time = init_time
        self.packet_queue = packet_queue
        self.server_callback = server_callback
        self.packet_counter = 0
        self.cmd_queue = []

        thread = threading.Thread(target = self.message_exchange_thread)
        thread.start()


    def add_cmd(self, cmd):
        self.cmd_queue.append(cmd)

    def message_exchange_thread(self):
        if self.type == Constant.TYPE_CSI_CLIENT:    # keep receiving CSI data from client and put them to the queue
            print('Connected new CSI client %s' % self.name)
            while True:
                pkt = self.connection.recv(Constant.BUFFER_SIZE)
                if len(pkt) == 0:
                    print('Disconnected CSI client %s' % self.name)
                    break

                if len(pkt) < 100:  # control message
                    cmd = msg.decode('UTF-8')


                self.packet_counter += 1
                elapsed_time = time.time() - self.init_time
                print('%.2fs: packet num: %d (%d bytes) from %s (%s)' % (elapsed_time, self.packet_counter, len(pkt), self.name, self.ip))
                self.packet_queue.put((elapsed_time, self.name, pkt))

        elif self.type == Constant.TYPE_FILE_TRANSFER_CLIENT:
            print('Connected new client for file transfer %s' % self.name)
            # Not yet supported
        
        elif self.type == Constant.TYPE_ANDROID_CLIENT:
            print('Connected new client for status check %s' % self.name)
            while True:
                msg = self.connection.recv(Constant.BUFFER_SIZE)
                if len(msg) == 0:
                    print('Disconnected status check client %s' % self.name)
                    break
                
                tmp = msg.decode('UTF-8').split(', ')    # get command
                cmd = tmp[0]

                if cmd == 'CMD_STATUS':
                    self.connection.send(str.encode(self.server_callback((Constant.EVENT_SERVER_STATUS,)))) 
                elif cmd == 'CMD_GET_TIME': # return time in ms
                    self.connection.send(str.encode('%d' % (time.time() * 1000)))                    
                elif cmd == 'CMD_START_CSI':
                    # make sure client sent 3 values separated by comma
                    if len(tmp) < 3:
                        self.connection.send(str.encode('Not enough arguments'))
                    else:
                        response = self.server_callback((Constant.EVENT_START_CSI, tmp[1], tmp[2], self.num))
                        self.connection.send(str.encode(response))
                elif cmd == 'CMD_STOP_CSI':
                    response = self.server_callback((Constant.EVENT_STOP_CSI, self.num))
                    self.connection.send(str.encode(response))
                else:
                    print('Undefined command: %s' % cmd)
                    self.connection.send(str.encode('Undefined command: %s' % cmd))

        # close connection
        self.connection.close()
        self.server_callback((Constant.EVENT_CLOSE_CONNECTION, self.num))
