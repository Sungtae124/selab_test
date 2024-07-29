import os
from dotenv import load_dotenv
import paramiko
import socket


class Server:
    def __init__(self):
        load_dotenv()
        self.hostname = os.getenv('HOSTNAME')
        self.port = int(os.getenv('PORT'))
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')

    def list_remote_files(self, directory):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, self.port, self.username, self.password)
            sftp = ssh.open_sftp()
            try:
                file_list = sftp.listdir(directory)
            except FileNotFoundError:
                print(f"FileNotFoundError: The directory {directory} does not exist.")
                raise
            sftp.close()
            ssh.close()
            return file_list
        except socket.gaierror as e:
            print(f"Socket error: {e}. Please check the server hostname.")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

    def read_remote_file(self, file_path):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.hostname, self.port, self.username, self.password)
            sftp = ssh.open_sftp()
            remote_file = sftp.open(file_path, 'r')
            content = remote_file.read().decode('utf-8')
            remote_file.close()
            sftp.close()
            ssh.close()
            return content
        except FileNotFoundError as e:
            print(f"FileNotFoundError: The file {file_path} does not exist.")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise
