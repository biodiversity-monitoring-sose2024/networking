import socket, os, sys, threading

def send_home(home_sock, data_length, data_to_send):
    home_sock.connect((home_IP, home_Port))
    #data_length = len(data_to_send)
    home_sock.sendall(data_length.to_bytes(4, 'big') + data_to_send)
    home_sock.close()

def check_files():
    for path in os.listdir(source_dir):
        if os.path.isfile(os.path.join(source_dir, path)):
            files_to_send.append(path)



if __name__ == '__main__':
    
    #home_IP="192.168.8.156"
    #home_IP="192.168.178.50"
    home_IP="192.168.8.170"
    home_Port= 5001
    files_to_send = []
    source_dir = './send_home/'
    move_dir = './sent/'
    thread_count = 0

    #home_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    threads = []
    #home_socks = []
    # home_sock.connect((home_IP, home_Port))
    #while True:
    check_files()
    for file in files_to_send:
        pid = os.fork()
        if pid == 0:

        #if len(threads) <= 4:
            filetotransfer = open(source_dir + file, 'rb')
            data_length = os.stat(source_dir + file).st_size
            data_to_send = filetotransfer.read()
            file_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #home_socks.append(file_sock)
            #t = threading.Thread(target=send_home, args=(file_sock, data_length, data_to_send))
            #t.start()
            #threads.append(t)
            # str(data_to_send).encode('utf-8')
            send_home(file_sock, data_length, str(data_to_send).encode('utf-8'))
            filetotransfer.close()
            # os.replace(source_dir + file, move_dir + file)
            files_to_send.remove(file)
            sys.exit()
        #else:
            #print('Max amount of threads already active')
                



        # So ists nur single
        # for path in os.listdir('./send_home'):
        #     filetotransfer = open('send_home/testsound.wav', 'rb')
        #     data_length = os.stat('send_home/testsound.wav').st_size
        #     #data_length = file_stats.st_size
        #     print('Länge: ' + str(data_length))
        #     data_to_send = filetotransfer.read()
        #     print(files_to_send)
        #     print(len(files_to_send))
        #     send_home(data_length, data_to_send)
        #     filetotransfer.close()
        #     # os.replace("send_home/" + path, "sent/" + path) #Move or delete file from Disk
        #     sys.exit()
        #     #files_count -= 1
        #home_sock.close()
