from Server import Server

try:
    server = Server()
    server.run()        # run server
except:
    exit()              # exit program if failed to run server
