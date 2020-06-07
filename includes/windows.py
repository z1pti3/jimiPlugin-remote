from winrm.protocol import Protocol
import smbclient
from pathlib import Path

class windows():

    def __init__(self, host, username="administrator", password=""):
        self.host = host
        self.client, self.clientShell = self.connect(host,username,password)
        self.smb = self.connectSMB(host,username,password)
        
    def connect(self,host,username,password):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password)
        try:
            clientShell = client.open_shell()
        except:
            return (None, None)
        return (client, clientShell)

    def connectSMB(self,host,username,password):
        try:
            smbclient.register_session(host, username=username, password=password)
        except:
            return None
        return True

    def disconnect(self):
        if self.client:
            self.client.close_shell(self.clientShell)
            self.client = None

        if self.smb:
            smbclient.delete_session(self.host)
            self.smb = None

    def command(self, command, args=[], elevated=False):
        if self.client and self.clientShell:
            commandId = self.client.run_command(self.clientShell,command, args)
            stdout, stderr, exitCode = self.client.get_command_output(self.clientShell, commandId)
            self.client.cleanup_command(self.clientShell, commandId)
            response = stdout.decode().strip()
            errors = stderr.decode().strip()
            return (exitCode, response, errors)

    def upload(self,localFile,remotePath):
        if self.smb:
            f = open(localFile, mode="r")
            try:
                remoteFile = smbclient.open_file("\\{0}\{1}".format(self.host,remotePath), mode="w")
                while True:
                    part = f.read(4096)
                    if not part:
                        break
                    remoteFile.write(part)
                remoteFile.close()
                f.close()
                return True
            except:
                pass
        return False

    def download(self,remoteFile,localPath):
        if self.smb:
            f = open(localPath, mode="w")
            try:
                remoteFile = smbclient.open_file("\\{0}\{1}".format(self.host,remoteFile), mode="r")
                while True:
                    part = remoteFile.read(4096)
                    if not part:
                        break
                    f.write(part)
                remoteFile.close()
                f.close()
                return True
            except:
                pass
        return False

    def __del__(self):
        self.disconnect()
