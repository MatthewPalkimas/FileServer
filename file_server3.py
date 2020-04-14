import socket
import os

FILE_SERVER_NUMBER = 3
rn = '\r\n'


class FileServer:
    def __init__(self, ip='127.0.0.1', port=51130):
        self.orig_sock = socket.socket()
        self.ip = ip
        self.port = port + FILE_SERVER_NUMBER
        self.orig_sock.bind((self.ip, self.port))
        self.ssoc = None
        self.not_connected = True
        self.file_storage_path = os.path.join(os.getcwd(), "files_" + str(FILE_SERVER_NUMBER))
        if not os.path.exists(self.file_storage_path):
            os.mkdir(self.file_storage_path)
        self.current_user_database = None
        self.return_code = None
        self.start()

    def start(self):
        self.orig_sock.listen(5)
        while self.return_code != 'SHUTDOWN':
            print("Listening on port", self.port)
            self.ssoc, raddr = self.orig_sock.accept()
            self.get_ready()

    def restart(self):
        self.orig_sock.close()
        self.not_connected = True
        return 'RESTART'

    def get_ready(self):
        self.current_user_database = os.path.join(self.file_storage_path,
                                                  self.ssoc.recv(1000).decode("utf-8"))
        print("Now accessing user database at path:", self.current_user_database)
        if not os.path.exists(self.current_user_database):
            os.mkdir(self.current_user_database)
            print("User database at path", self.current_user_database, "created")
        self.ready_to_recv()

    def ready_to_recv(self):
        while True:
            data = self.ssoc.recv(1000).decode("utf-8")
            data = data.split("\r\n")
            if data[0] == 'LOGOUT':
                self.get_ready()
            elif data[0] == 'STR':
                self.ssoc.sendall(b'\x00')
                self.store_parse(data[1:])
                self.ssoc.sendall(b'\x00')
            elif data[0] == 'RTV':
                self.retrieve_parse(data[1:])
            elif data[0] == 'DEL':
                self.delete_parse(data[1:])
                self.ssoc.sendall(b'\x00')

    def store_parse(self, data):
        file_name = data[1]
        file_path = data[2]
        file_size = int(data[0])
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        print("attempting to do store_parse for", file_size, "bytes", FILE_SERVER_NUMBER)
        if not os.path.exists(actual_file_directory):
            os.mkdir(actual_file_directory)
            print("created directory at", actual_file_directory)
        try:
            f = open(actual_file_path, "wb+")
            cur_file_size_read = 0
            temp = file_size / 1000
            extra = file_size % 1000
            while cur_file_size_read < file_size:
                if not temp:
                    file_data = self.ssoc.recv(extra)
                else:
                    file_data = self.ssoc.recv(1000)
                f.write(file_data)
                cur_file_size_read += len(file_data)
                temp -= 1
            print("read", cur_file_size_read, "bytes")
            f.close()
            return "File " + file_name + " successfully created and written to in directory " + actual_file_path
        except:
            return "Something went wrong during file process"

    def retrieve_parse(self, data):
        file_name = data[0]
        file_path = data[1]
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        if not os.path.exists(actual_file_directory):
            return "ERROR the file path you gave did not exist in the file system!"
        if not os.path.exists(actual_file_path):
            return "ERROR the file name you gave did not exist in the file system!"
        self.ssoc.sendall((str(os.path.getsize(actual_file_path)) + rn).encode("utf-8"))
        print("Sending file size", str(os.path.getsize(actual_file_path)), FILE_SERVER_NUMBER)
        try:
            f = open(actual_file_path, "rb")
            file_contents = f.read()
            self.ssoc.sendall(file_contents)
            f.close()
            return "Successfully sent full file"
        except:
            return "Something went wrong during file process"

    def delete_parse(self, data):
        file_name = data[0]
        file_path = data[1]
        actual_file_directory = os.path.join(self.current_user_database, file_path)
        actual_file_path = os.path.join(actual_file_directory, file_name)
        if not os.path.exists(actual_file_directory) or not os.path.exists(actual_file_path):
            return "ERROR The file path or file name you gave did not exist in the file system!"
        try:
            os.remove(actual_file_path)
            return "Successfully removed file " + file_name + " from the file system"
        except:
            return "Something went wrong during file process"


if __name__ == "__main__":
    fserv = FileServer()
