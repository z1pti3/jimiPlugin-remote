from paramiko import SSHClient, RSAKey, AutoAddPolicy
from scp import SCPClient
from pathlib import Path
import os

class linux():
    client = None

    def __init__(self, host, username="root", keyFile='', password=''):
        self.error = ""
        if keyFile != '':
            self.client = self.connect(host,username,keyFile=str(Path(keyFile)))
        else:
            self.client = self.connect(host,username,password=password)
        if self.client:
            self.scp = self.connectSCP(self.client)
        
    def connect(self, host, username, keyFile='', password=''):
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(AutoAddPolicy())
        try:
            if keyFile != '':
                client.connect(host, username=username, key_filename=keyFile, look_for_keys=True, timeout=5000)
            else:
                client.connect(host, username=username, password=password, look_for_keys=True, timeout=5000)
        except Exception as e:
            self.error = e
            return None
        return client

    def connectSCP(self, client):
        scp = SCPClient(client.get_transport())
        return scp

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def reboot(self,timeout):
        # Not implimented yet!
        pass

    def command(self, command, args=[], elevate=False):
        if self.client:
            if elevate:
                stdin, stdout, stderr = self.client.exec_command("sudo {0} {1}".format(command, " ".join(args)).strip())
            else:
                stdin, stdout, stderr = self.client.exec_command("{0} {1}".format(command, " ".join(args)).strip())
            exitCode = stdout.channel.recv_exit_status()
            response = stdout.readlines()
            errors = stderr.readlines()
            return (exitCode, response, errors)

    def upload(self, localFile, remotePath):
        if self.scp:
            try:
                self.scp.put(localFile,remotePath)
                return True
            except:
                return False
        return False

    def download(self, remoteFile, localPath, createMissingFolders):
        if self.scp:
            try:
                if createMissingFolders:
                    splitChar = "\\"
                    if splitChar not in localPath:
                        splitChar = "/"
                    if not os.path.isdir(localPath.rsplit(splitChar,1)[0]):
                        os.makedirs(localPath.rsplit(splitChar,1)[0])
                self.scp.get(remoteFile,localPath)
                return True
            except:
                return False
        return False

    def __del__(self):
        self.disconnect()
