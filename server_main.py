import socket
import datetime
import time
import os
import glob
import random

VALID_OPCODES = ['STR', 'RTV', 'DEL', 'INF', 'LGO']
'''
STR
    Store a file
    file name\r\nfile path\r\nfile size\r\n\r\n
RTV
    Retrieve a file
    file name\r\nfile path\r\n\r\n
    server sends file size ---> client receives that many bytes
DEL
    Delete a file
    file name\r\nfile path\r\n\r\n
INF
    Get info of all files in database
LGO
    Logout of the server and go back to login screen
'''

rn = "\r\n"


class InvalidOpCode(Exception):
    pass


class RecievedPartial(Exception):
    pass


class MyServer:
    def __init__(self, ip='127.0.0.1', port=17777):
        self.data_server_sockets = [socket.socket(), socket.socket(), socket.socket(), socket.socket()]
        self.connect_to_data_servs()
        self.orig_sock = socket.socket()
        self.csoc = None
        self.ip = ip
        self.port = port
        self.orig_sock.bind((self.ip, self.port))
        self.start()
        self.connection_time = datetime.datetime.utcnow()
        self.username = None
        self.password = None
        # was commenting this out since if something goes wrong I dont want it to mess anything up...
        self.user_database = os.path.join(os.getcwd(), "user_database")
        if not os.path.exists(self.user_database):
            os.mkdir(self.user_database)
        # self.user_database = os.path.join("C:\\Users\\Matthew\\Desktop\\ECE470\\Project1", "files")
        self.current_user_database = None
        print("Client connected to Server Palk @", self.connection_time)
        self.restart()

    def connect_to_data_servs(self):
        list_of_dservs = [1, 2, 3, 4]
        while True:
            for dserv in list_of_dservs:
                try:
                    self.data_server_sockets[dserv - 1].connect(('127.0.0.1', (51130 + dserv)))
                except:
                    print("could not connect to data server", dserv)
                    continue
                print("connected to data server", dserv)
                list_of_dservs.remove(dserv)
                break
            if not list_of_dservs:
                break
        print("Connected to all data servers.")

    def start(self):
        self.orig_sock.listen(5)
        print("Listening on ", self.port)
        commsoc, raddr = self.orig_sock.accept()
        self.csoc = commsoc

    def restart(self):
        login = self.login()
        if not login:
            return
        self.update_data_servs()
        self.reading_commands()

    def login(self):
        not_logged_in = True
        server_user_pass_mess = "2" + rn + "Username: " + rn + "Password: " + rn
        hello_message = self.csoc.recv(1000).decode("utf-8")
        if hello_message != "HI\r\n\r\n":
            return False
        else:
            self.csoc.sendall(("HI\r\n" + server_user_pass_mess + rn).encode("utf-8"))
        while not_logged_in:
            # ask user for username and password
            username_password = self.csoc.recv(1000).decode("utf-8")
            username_password = username_password.split("\r\n")
            if len(username_password) != 4 and username_password[-2:] != ['', '']:
                self.csoc.sendall(("E\r\nBadly Formatted Message\r\n"
                                   + server_user_pass_mess + rn).encode("utf-8"))
                continue
            self.username = username_password[0]
            password = username_password[1]
            if self.username not in os.listdir(self.user_database):
                self.csoc.sendall(("E\r\nUsername does not exist in database!\r\n"
                                   + "1\r\nDo you want to create an account (YES or NO): \r\n" + rn).encode("utf-8"))
                response = self.csoc.recv(1000).decode("utf-8").split('\r\n')
                if response[0] == "YES":
                    self.csoc.sendall("L\r\n3\r\nEnter Desired Username: \r\nEnter password:" 
                                      " \r\nConfirm password: \r\n\r\n".encode("utf-8"))
                    response = self.csoc.recv(1000).decode("utf-8").split("\r\n")
                    self.current_user_database = os.path.join(self.user_database, response[0])
                    while os.path.exists(self.current_user_database):
                        self.csoc.sendall("E\r\n"
                                          "Username already exists in database!"
                                          "\r\n"
                                          "3"
                                          "\r\n"
                                          "Enter Desired Username: "
                                          "\r\n"
                                          "Enter password:"
                                          " \r\n"
                                          "Confirm password: "
                                          "\r\n\r\n".encode("utf-8"))
                        response = self.csoc.recv(1000).decode("utf-8").split("\r\n")
                        self.current_user_database = os.path.join(self.user_database, response[0])
                    os.mkdir(self.current_user_database)
                    print(self.current_user_database)
                    pass1 = response[1]
                    pass2 = response[2]
                    while pass1 != pass2:
                        self.csoc.sendall("E\r\n"
                                          "Passwords did not match..."
                                          "\r\n"
                                          "2"
                                          "\r\n"
                                          "Enter password:" 
                                          " \r\n"
                                          "Confirm password: "
                                          "\r\n\r\n".encode("utf-8"))
                        response = self.csoc.recv(1000).decode("utf-8").split("\r\n")
                        pass1 = response[0]
                        pass2 = response[1]
                    password = response[1]
                    password_file = open(os.path.join(self.current_user_database, "password.txt"), "w+")
                    password_file.write(password)
                    password_file.close()
                else:
                    self.csoc.sendall(("HI\r\n" + server_user_pass_mess + rn).encode("utf-8"))
                    continue
            print("User ", self.username, " attempting to login.")
            self.current_user_database = os.path.join(self.user_database, self.username)
            if self.check_password(password):
                print("user logged in")
                not_logged_in = False
                self.csoc.sendall(("S\r\nWelcome " + self.username + "! You are a legend...\r\n").encode("utf-8"))
            else:
                incorrect_pass = "E\r\nPassword did not match username " + self.username + rn \
                                                                         + server_user_pass_mess + rn
                self.csoc.sendall(incorrect_pass.encode("utf-8"))
        return True

    def update_data_servs(self, logout=False):
        if logout:
            for dserv in self.data_server_sockets:
                dserv.send("LOGOUT".encode("utf-8"))
        else:
            for dserv in self.data_server_sockets:
                dserv.send(self.username.encode("utf-8"))

    def reading_commands(self):
        while True:
            try:
                data = self.csoc.recv(1000)
            except ConnectionResetError:
                break
            message_back = self.manipulate_data(data.decode("utf-8"), data)
            time.sleep(0.5)
            self.csoc.sendall(message_back.encode("utf-8"))
        print("Client Ended Connection @", datetime.datetime.utcnow())

    def manipulate_data(self, data_recv, raw_data):
        self.opcode = data_recv[0:3]
        if self.opcode not in VALID_OPCODES:
            return "ERROR Opcode was invalid!"
        entire_data = self.apply_opcode_to_parse(data_recv)
        return entire_data

    def store_parse(self, data):
        file_name = data[0]
        file_path = data[1]
        file_size = int(data[2])
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        if not os.path.exists(actual_file_directory):
            os.mkdir(actual_file_directory)
        try:
            f = open('temp.temp', "wb+")
            p = open(actual_file_path, "wb+")
            # this is just for the INF
            p.close()
            cur_file_size_read = 0
            temp = file_size / 1000
            extra = file_size % 1000
            while cur_file_size_read < file_size:
                if not temp:
                    file_data = self.csoc.recv(extra)
                else:
                    file_data = self.csoc.recv(1000)
                f.write(file_data)
                cur_file_size_read += len(file_data)
                temp -= 1
            print("read", cur_file_size_read, "bytes")
            f.close()
            f = open('temp.temp', 'rb')
            temp_byte_array = f.read()
            f.close()
            os.remove('temp.temp')
            div_by_4 = cur_file_size_read % 4
            if div_by_4 == 0:
                padding = b'\x04\x04\x04\x04'
                file_size += 4
            elif div_by_4 == 3:
                padding = b'\x01'
                file_size += 1
            elif div_by_4 == 2:
                padding = b'\x02\x02'
                file_size += 2
            else:
                padding = b'\x03\x03\x03'
                file_size += 3
            temp_byte_array += padding
            file_name_endings = ['A1', 'A2', 'B1', 'B2', 'O1', 'O2', 'O3', 'O4']
            four_divisions = {'A1': b'', 'A2': b'', 'B1': b'', 'B2': b'',
                              'O1': b'', 'O2': b'', 'O3': b'', 'O4': b'',
                              '_A1': '', '_A2': '', '_B1': '', '_B2': '',
                              '_O1': '', '_O2': '', '_O3': '', '_O4': ''}
            for i, _end in enumerate(file_name_endings):
                file_name_div = file_name.split('.')
                temp_file_name = file_name_div[0] + '_' + _end
                for ext in file_name_div[1:]:
                    temp_file_name = temp_file_name + '.' + ext
                four_divisions[('_' + _end)] += temp_file_name
                if i < 4:
                    begin = int(i * (file_size / 4))
                    end = int((i + 1) * (file_size / 4))
                    four_divisions[_end] += temp_byte_array[begin:end]
                else:
                    four_divisions[_end] = bytearray(len(four_divisions['A1']))
                    for bit in range(len(four_divisions[_end])):
                        if _end == 'O1':
                            four_divisions[_end][bit] = four_divisions['A1'][bit] ^ four_divisions['B1'][bit]
                        elif _end == 'O2':
                            four_divisions[_end][bit] = four_divisions['A2'][bit] ^ four_divisions['B2'][bit]
                        elif _end == 'O3':
                            four_divisions[_end][bit] = four_divisions['A2'][bit] ^ four_divisions['B1'][bit]
                        elif _end == 'O4':
                            four_divisions[_end][bit] = (four_divisions['A1'][bit] ^ four_divisions['A2'][bit]) \
                                                        ^ four_divisions['B2'][bit]
            for i, data_server in enumerate(self.data_server_sockets):
                if i == 0:
                    print("sending A1, A2 to server 1")
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_A1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['A1'])
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_A2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['A2'])
                    pause_recv = data_server.recv(1)
                elif i == 1:
                    print("sending B1, B2 to server 2")
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_B1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['B1'])
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_B2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['B2'])
                    pause_recv = data_server.recv(1)
                elif i == 2:
                    print("sending O1, O2 to server 3")
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_O1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['O1'])
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_O2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['O2'])
                    pause_recv = data_server.recv(1)
                elif i == 3:
                    print("sending O3, O4 to server 4")
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_O3'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['O3'])
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + str(int(file_size / 4)) + rn + four_divisions['_O4'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    data_server.sendall(four_divisions['O4'])
                    pause_recv = data_server.recv(1)
            return "File " + file_name + " successfully created and written to"
        except Exception as e:
            print(e)
            return "E Something went wrong during file process"

    def retrieve_parse(self, data):
        file_name = data[0]
        file_path = data[1]
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        if not os.path.exists(actual_file_directory):
            return "ERROR the file path you gave did not exist in the file system!"
        if not os.path.exists(actual_file_path):
            return "ERROR the file name you gave did not exist in the file system!"
        try:
            file_name_endings = ['A1', 'A2', 'B1', 'B2', 'O1', 'O2', 'O3', 'O4']
            four_divisions = {'A1': '', 'A2': '', 'B1': '', 'B2': '',
                              'O1': '', 'O2': '', 'O3': '', 'O4': ''}
            for i, _end in enumerate(file_name_endings):
                file_name_div = file_name.split('.')
                temp_file_name = file_name_div[0] + '_' + _end
                for ext in file_name_div[1:]:
                    temp_file_name = temp_file_name + '.' + ext
                four_divisions[_end] += temp_file_name
            random_server = [0, 1, 2, 3]
            chosen_servers = random.sample(set(random_server), 2)
            print("Retrieving from servers:", chosen_servers[0]+1, chosen_servers[1]+1)
            file_data = {'A1': b'', 'A2': b'', 'B1': b'', 'B2': b'',
                         'O1': b'', 'O2': b'', 'O3': b'', 'O4': b''}
            for fs in chosen_servers:
                if fs == 0:
                    ends = ['A1', 'A2']
                elif fs == 1:
                    ends = ['B1', 'B2']
                elif fs == 2:
                    ends = ['O1', 'O2']
                else:
                    ends = ['O3', 'O4']
                print("receiving data from server", fs + 1)
                for end in ends:
                    cur_file_size_read = 0
                    first_mess = self.opcode + rn + four_divisions[end] \
                        + rn + file_path + rn + rn
                    self.data_server_sockets[fs].sendall(first_mess.encode('utf-8'))
                    file_size = int(self.data_server_sockets[fs].recv(1000).decode('utf-8').split('\r\n')[0])
                    print("got back file size of", file_size)
                    temp = file_size / 1000
                    extra = file_size % 1000
                    while cur_file_size_read < file_size:
                        if not temp:
                            data = self.data_server_sockets[fs].recv(extra)
                        else:
                            data = self.data_server_sockets[fs].recv(1000)
                        file_data[end] += data
                        cur_file_size_read += len(data)
                        temp -= 1
            file_data = self.undo_xor_if_applicable(chosen_servers, file_data)
            _padding = file_data['B2'][-1]
            _padding = _padding * -1
            file_data['B2'] = file_data['B2'][:_padding]
            entire_file = file_data['A1'] + file_data['A2'] + file_data['B1'] + file_data['B2']
            self.csoc.sendall((str(len(entire_file)) + rn).encode("utf-8"))
            self.csoc.sendall(entire_file)
            return "Successfully retrieved file " + file_name + " from the file system"
        except Exception as e:
            print(e)
            return "E Something went wrong during file process"

    def delete_parse(self, data):
        file_name = data[0]
        file_path = data[1]
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        if not os.path.exists(actual_file_directory) or not os.path.exists(actual_file_path):
            return "ERROR The file path or file name you gave did not exist in the file system!"
        try:
            os.remove(actual_file_path)
            file_name_endings = ['A1', 'A2', 'B1', 'B2', 'O1', 'O2', 'O3', 'O4']
            four_divisions = {'_A1': '', '_A2': '', '_B1': '', '_B2': '',
                              '_O1': '', '_O2': '', '_O3': '', '_O4': ''}
            for i, _end in enumerate(file_name_endings):
                file_name_div = file_name.split('.')
                temp_file_name = file_name_div[0] + '_' + _end
                for ext in file_name_div[1:]:
                    temp_file_name = temp_file_name + '.' + ext
                four_divisions[('_' + _end)] += temp_file_name
            for i, data_server in enumerate(self.data_server_sockets):
                if i == 0:
                    print("sending A1, A2 to server 1")
                    first_mess = self.opcode + rn + four_divisions['_A1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + four_divisions['_A2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                elif i == 1:
                    print("sending B1, B2 to server 2")
                    first_mess = self.opcode + rn + four_divisions['_B1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + four_divisions['_B2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                elif i == 2:
                    print("sending O1, O2 to server 3")
                    first_mess = self.opcode + rn + four_divisions['_O1'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + four_divisions['_O2'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                elif i == 3:
                    print("sending O3, O4 to server 4")
                    first_mess = self.opcode + rn + four_divisions['_O3'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
                    first_mess = self.opcode + rn + four_divisions['_O4'] \
                                 + rn + file_path + rn + rn
                    data_server.sendall(first_mess.encode('utf-8'))
                    pause_recv = data_server.recv(1)
            return "Successfully removed file " + file_name + " from the file system"
        except:
            return "E Something went wrong during file process"

    def info_parse(self):
        all_files = glob.glob(os.path.join(self.current_user_database, "**", "*"), recursive=True)
        if  len(all_files) == 1:
            return "No files in database"
        file_info = ""
        for f in all_files:
            if "password.txt" in f:
                continue
            path = f.split(self.user_database)[1]
            file_info = file_info + path + "\n"
        return file_info

    def apply_opcode_to_parse(self, data):
        if self.opcode == 'STR':
            print("Storing file code")
            entire_data = data.split('\r\n')[1:]
            if len(entire_data) != 5 or entire_data[-2:] != ['', '']:
                return "ERROR Did not receive all the parameters required for opcode:" + self.opcode
            return self.store_parse(entire_data)
        elif self.opcode == 'RTV':
            print("Retrieving file code")
            entire_data = data.split('\r\n')[1:]
            if len(entire_data) != 4 or entire_data[-2:] != ['', '']:
                return "ERROR Did not receive all the data!"
            return self.retrieve_parse(entire_data)
        elif self.opcode == 'DEL':
            print("Deleting file code")
            entire_data = data.split('\r\n')[1:]
            if len(entire_data) != 4 or entire_data[-2:] != ['', '']:
                return "ERROR Did not receive all the data!"
            return self.delete_parse(entire_data)
        elif self.opcode == 'INF':
            return self.info_parse()
        elif self.opcode == 'LGO':
            print("Logging out now")
            self.update_data_servs(logout=True)
            self.restart()

    def undo_xor_if_applicable(self, servers, all_data):
        """
        O1 = A1 ^ B1
        O2 = A2 ^ B2
        O3 = A2 ^ B1
        O4 = A1 ^ A2 ^ B2
        """
        four_parts = {'A1': b'', 'A2': b'', 'B1': b'', 'B2': b''}
        if 0 in servers:
            four_parts['A1'] = all_data['A1']
            four_parts['A2'] = all_data['A2']
            if 1 in servers:
                return all_data
            elif 2 in servers:
                four_parts['B1'] = bytearray(len(all_data['A1']))
                for bit in range(len(four_parts['B1'])):
                    four_parts['B1'][bit] = all_data['A1'][bit] ^ all_data['O1'][bit]
                four_parts['B2'] = bytearray(len(all_data['A2']))
                for bit in range(len(four_parts['B1'])):
                    four_parts['B2'][bit] = all_data['A2'][bit] ^ all_data['O2'][bit]
            elif 3 in servers:
                four_parts['B1'] = bytearray(len(all_data['A2']))
                for bit in range(len(four_parts['B1'])):
                    four_parts['B1'][bit] = all_data['A2'][bit] ^ all_data['O3'][bit]
                four_parts['B2'] = bytearray(len(all_data['A2']))
                for bit in range(len(four_parts['B2'])):
                    four_parts['B2'][bit] = (all_data['A2'][bit] ^ all_data['O4'][bit]) ^ all_data['A1'][bit]
        elif 1 in servers:
            four_parts['B1'] = all_data['B1']
            four_parts['B2'] = all_data['B2']
            if 2 in servers:
                four_parts['A1'] = bytearray(len(all_data['B1']))
                for bit in range(len(four_parts['A1'])):
                    four_parts['A1'][bit] = all_data['B1'][bit] ^ all_data['O1'][bit]
                four_parts['A2'] = bytearray(len(all_data['B2']))
                for bit in range(len(four_parts['A2'])):
                    four_parts['A2'][bit] = all_data['B2'][bit] ^ all_data['O2'][bit]
            elif 3 in servers:
                four_parts['A2'] = bytearray(len(all_data['B2']))
                for bit in range(len(four_parts['A2'])):
                    four_parts['A2'][bit] = all_data['B1'][bit] ^ all_data['O3'][bit]
                four_parts['A1'] = bytearray(len(all_data['B1']))
                for bit in range(len(four_parts['B1'])):
                    four_parts['A1'][bit] = (all_data['B2'][bit] ^ all_data['O4'][bit]) ^ four_parts['A2'][bit]
        else:
            four_parts['A1'] = bytearray(len(all_data['O1']))
            four_parts['A2'] = bytearray(len(all_data['O1']))
            four_parts['B1'] = bytearray(len(all_data['O1']))
            four_parts['B2'] = bytearray(len(all_data['O1']))
            for bit in range(len(four_parts['A1'])):
                four_parts['A1'][bit] = all_data['O2'][bit] ^ all_data['O4'][bit]
            for bit in range(len(four_parts['B1'])):
                four_parts['B1'][bit] = four_parts['A1'][bit] ^ all_data['O1'][bit]
            for bit in range(len(four_parts['A2'])):
                four_parts['A2'][bit] = four_parts['B1'][bit] ^ all_data['O3'][bit]
            for bit in range(len(four_parts['B2'])):
                four_parts['B2'][bit] = four_parts['A2'][bit] ^ all_data['O2'][bit]
        return four_parts

    def check_password(self, password):
        try:
            pass_file = open(os.path.join(self.current_user_database, "password.txt"), "r")
        except:
            return False
        correct_password = pass_file.read()
        if password != correct_password:
            return False
        else:
            return True


if __name__ == "__main__":
    da_server = MyServer()
    # # wait for incoming connections
    # while True:
    #     print("Listening on ", port)
    #
    #     commsoc, raddr = serversoc.accept()
    #
    #     MyServer(commsoc)
    #
    #     commsoc.close()
    #
    # # close the server socket
    # serversoc.close()
