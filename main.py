from ast import ExceptHandler
from Server import Server
from Client import Client
import sys

# check if input arguments are correct
flag_server = False
host = None
port = None
ch = 13
bw = 20

try:
    if sys.argv[1] == 'server':
        flag_server = True
    idx = 2
    while idx < len(sys.argv):
        if sys.argv[idx] == '-h':
            host = sys.argv[idx+1]
        elif sys.argv[idx] == '-p':
            port = int(sys.argv[idx+1])
        elif sys.argv[idx] == '-c':
            ch = int(sys.argv[idx+1])
        elif sys.argv[idx] == '-b':
            bw = int(sys.argv[idx+1])
        else:
            raise Exception('Unknown input options')
        idx += 2
    if flag_server and (host is None or port is None):
        raise Exception('Unknown host or port')

except Exception as e:
    print('[Error] Wrong input arguments (%s)' % str(e))
    print('Usage: python3 main.py [server/client] [options]')
    print('Options: -h host')
    print('         -p port')
    print('         -c channel (client only)')
    print('         -b bandwidth (client only)')
    print('ex) python3 main.py server -h 127.0.0.1 -p 5000')
    print('ex) sudo python3 main.py client -h 127.0.0.1 -p 5000 -c 6 -b 20')
    print('ex) sudo python3 main.py client -c 6 -b 20 (results will be stored in local device)')
    exit()



## run server/client program
if flag_server:
    try:
        server = Server(host, port)
        server.run()
    except Exception as e:
        print('Failed to run server (%s)' % str(e))
        exit()

else:
    try:
        client = Client(host, port, ch, bw)
        client.run()
    except Exception as e:
        print('Failed to run client program (%s)' % str(e))
        exit()