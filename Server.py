import socket
import time
import threading
import multiprocessing
from Filewriter import Filewriter

host = 'icsl.knu.ac.kr'
port = 50001

client_timeout = 10     # close connection if client is inactive for this time[s]
handshake_key = 'vkjdo9uj2lk3j4lkjlbiudi8029384llkcnp098lksjelkj3'  # only accept client providing this key
buffer_size = 2048      # buffer size [bytes]

class Server:
    client_counter = 0      # number of active clients
    client_list = []        # list of active clients

    def __init__(self):
        self.server_socket = socket.socket()
        try:
            self.server_socket.bind((host, port))   # open server socket
        except socket.error as e:
            print(str(e))
            raise Exception('Server is not ready !')
        
    
    def run(self):                      # listen socket and accept new clients
        self.server_socket.listen()
        print('Server is listening on the port %d' % port)
        while True:
            self.accept_connection()
            time.sleep(0.01)

    
    def accept_connection(self):        # accept new connection
        connection, addr = self.server_socket.accept()

        if len(self.client_list) == 0:  # if this client is the first one -> reset counter, queue, filewriter, etc.
            self.client_counter = 0
            self.packet_queue = multiprocessing.Manager().Queue()   # prepare new queue
            self.init_time = time.time()
            self.filewriter = Filewriter(self.packet_queue)         # create new file
            self.filewriter.start()
            
        self.client_counter += 1        # add this client to the list
        client = Client(self.client_counter, connection, addr, self.init_time, self.packet_queue, self.close_connection)
        self.client_list.append(client)
    

    def close_connection(self, num):    # remove client which number is 'num'
        for i in range(len(self.client_list)):
            if self.client_list[i].num == num:
                self.client_list.pop(i)
                break
        if len(self.client_list) == 0:  # if no client is connected -> stop writing file
            self.packet_queue.put((-1, b'name', b'end'))



class Client:
    def __init__(self, num, connection, addr, init_time, packet_queue, close_callback):
        self.num = num
        self.connection = connection
        self.ip = addr[0]
        self.port = addr[1]
        self.init_time = init_time
        self.packet_queue = packet_queue
        self.close_callback = close_callback    # callback function will be called when connection is ended
        self.packet_counter = 0

        thread = threading.Thread(target = self.message_exhange_thread)
        thread.start()


    def message_exhange_thread(self):
        self.connection.send(str.encode('You are connected to icsl server. Send your name'))
        self.name = self.get_packet().decode('utf-8')
        self.connection.send(str.encode('Send handshake key'))
        try:
            received_handshake_key = self.get_packet().decode('utf-8')  # check handshake key -> if wrong, disconnect
            if handshake_key == received_handshake_key:
                print('New client connected (%s:%d)' % (self.ip, self.port))
                # keep receiving messages from client
                while True:                                         # enter a loop to exchange message
                    pkt = self.get_packet()
                    self.connection.send(str.encode('received'))               
                    
                    self.packet_counter += 1
                    elapsed_time = time.time() - self.init_time
                    print('%.2fs: packet num: %d (%d bytes) from %s (%s)' % (elapsed_time, self.packet_counter, len(pkt), self.name, self.ip))
                    self.packet_queue.put((elapsed_time, self.name, pkt))
            else:
                print('client (%s:%d) treid to connect, but handshake was failed' % (self.ip, self.port))

        except Exception as e:
            print(str(e))
        
        # close connection
        self.connection.close()
        self.close_callback(self.num)
                
        
    def get_packet(self):
        begin_time = time.time()
        while True:
            pkt = self.connection.recv(buffer_size)
            if len(pkt) == 0:
                if time.time() - begin_time >= client_timeout:
                    raise Exception('connection timeout')
                time.sleep(0.001)
                continue
            else:
                break
        return pkt

