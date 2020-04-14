import socket
import os

rn = "\r\n"


class SizeOfFileError(Exception):
    pass


def do_client_stuff(csoc):
    not_done = True
    local_filesys_path = os.path.join(os.getcwd(), "c_files")
    if not os.path.exists(local_filesys_path):
        os.mkdir(local_filesys_path)
    print("---------------------------------------------------------------------------\n"
          "| Hello client, you have connected to Server Palk. Note: this will change |\n"
          "|  All files need to be inside a directory inside the c_files directory!  |\n"
          "---------------------------------------------------------------------------")
    not_logged_in = True
    csoc.sendall("HI\r\n\r\n".encode("utf-8"))
    while not_logged_in:
        server_message = csoc.recv(1000).decode("utf-8").split("\r\n")
        code = server_message[0]
        code_flag = 0
        if code == 'E':
            code_flag = 1
            error_message = server_message[1]
            print(error_message)
        elif code == 'S':
            print(server_message[1])
            break
        number_of_inputs = int(server_message[1 + code_flag])
        final_mess = ""
        for num_i in range(0, number_of_inputs):
            _input = input(server_message[num_i + 2 + code_flag])
            final_mess += _input + rn
        final_mess += rn
        csoc.sendall(final_mess.encode("utf-8"))
    while not_done:
        file_size = 0
        sending_file = False
        retrieving_file = False
        mess = input("Enter the operation you want to send to the server from the list below\n"
                     "  STR - Store a file on the server\n"
                     "  RTV - Retrieve a file from the server\n"
                     "  DEL - Delete a file from the server\n"
                     "  INF - See which files you have stored on the server\n"
                     "  LGO - Logout from the server\n"
                     "  ~ ")
        if mess == "STR":
            sending_file = True
        if mess == "RTV":
            retrieving_file = True
        if mess == "INF":
            inf_mess = "INF\r\n\r\n"
            csoc.sendall(inf_mess.encode("utf-8"))
            print("sent \"" + mess + "\" to the server")
            data = csoc.recv(1000)
            print("Server sent\n" + data.decode("utf-8"))
            continue
        if mess == "LGO":
            csoc.sendall("LGO\r\n\r\n".encode("utf-8"))
            return 'logout'
        file_name = input("Enter the file name: ")
        file_path = input("Enter the file path: ")
        file_dircetory_path = os.path.join(local_filesys_path, file_path)
        full_path = os.path.join(local_filesys_path, file_path, file_name)
        if sending_file:
            if not os.path.exists(full_path):
                print("file path was invalid!")
                continue
            file_size = os.path.getsize(full_path)
            whole_mess = mess + rn + file_name + rn + file_path + rn + str(file_size) + rn + rn
        else:
            whole_mess = mess + rn + file_name + rn + file_path + rn + rn
        csoc.sendall(whole_mess.encode("utf-8"))
        print("sent \"" + whole_mess + "\" to the server")
        if sending_file:
            print("now sending binary file!")
            f = open(full_path, "rb")
            file_data = f.read()
            if len(file_data) != file_size:
                raise SizeOfFileError
            csoc.sendall(file_data)
            f.close()
            data = csoc.recv(1000)
            print("received \"" + data.decode("utf-8") + "\" from the server")
        elif retrieving_file:
            data = csoc.recv(1000)
            file_size = data.decode("utf-8").split("\r\n")[0]
            if file_size[0] == 'E':
                print("got back:\n", file_size)
                continue
            else:
                file_size = int(file_size)
            print("retrieving file code of size", file_size)
            cur_file_size_read = 0
            if not os.path.exists(file_dircetory_path):
                os.mkdir(file_dircetory_path)
            f = open(full_path, "wb+")
            temp = file_size / 1000
            extra = file_size % 1000
            while cur_file_size_read < file_size:
                if not temp:
                    file_data = csoc.recv(extra)
                else:
                    file_data = csoc.recv(1000)
                f.write(file_data)
                cur_file_size_read += len(file_data)
                temp -= 1
            print("read", cur_file_size_read, "bytes")
            f.close()
            print(csoc.recv(1000).decode('utf-8'))
        else:
            data = csoc.recv(1000)
            print("received \"" + data.decode("utf-8") + "\" from the server")
    print("Ended baseTCPProtocol")
    return 'EXIT'


if __name__ == "__main__":
    # create the socket
    #  defaults family=AF_INET, type=SOCK_STREAM, proto=0, filno=None
    return_code = ''
    commsoc = socket.socket()
    # port = int(input("Enter the port your server is on: "))
    # connect to localhost:5000
    port = 17777
    commsoc.connect(("localhost", port))

    while return_code != 'EXIT':
        return_code = do_client_stuff(commsoc)

    # close the comm socket
    commsoc.close()

