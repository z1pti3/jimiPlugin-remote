from threading import Lock
from winrm.protocol import Protocol
import smbclient
from pathlib import Path
import os
import errno

# Cheat without using smbclient low level mode to detmine if the client is open for more than one flow
openConnections = {}
openConnectionsLock = Lock()

class windows():

    def __init__(self, host, username="administrator", password=""):
        self.host = host
        self.client, self.clientShell = self.connect(host,username,password)
        if self.client:
            self.smb = self.connectSMB(host,username,password)
        else:
            self.smb = None
        
    def connect(self,host,username,password):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password,read_timeout_sec=30)
        try:
            clientShell = client.open_shell()
        except:
            return (None, None)
        return (client, clientShell)

    def connectSMB(self,host,username,password):
        try:
            with openConnectionsLock:
                if host not in openConnections:
                    smbclient.register_session(host, username=username, password=password,connection_timeout=30)
                    openConnections[host] = 0
                openConnections[host]+=1
        except:
            return None
        return True

    def disconnect(self):
        if self.client:
            self.client.close_shell(self.clientShell)
            self.client = None

        with openConnectionsLock:
            if self.smb:
                if self.host in openConnections:
                    openConnections[self.host]-=1
                    if openConnections[self.host] == 0:
                        del openConnections[self.host]
                        smbclient.delete_session(self.host)
                        self.smb = None

    def command(self, command, args=[], elevate=False):
        if self.client and self.clientShell:
            commandId = self.client.run_command(self.clientShell,command, args)
            stdout, stderr, exitCode = self.client.get_command_output(self.clientShell, commandId)
            self.client.cleanup_command(self.clientShell, commandId)
            response = stdout.decode().strip()
            errors = stderr.decode().strip()
            return (exitCode, response, errors)

    def upload(self,localFile,remotePath):
        if self.smb:
            # single file
            if not os.path.isdir(localFile):
                f = open(localFile, mode="rb")
                remoteFile = smbclient.open_file("\\{0}\{1}".format(self.host,remotePath), mode="wb")
                try:
                    while True:
                        part = f.read(4096)
                        if not part:
                            break
                        remoteFile.write(part)
                except:
                    return False
                finally:
                    remoteFile.close()
                    f.close()
                return True
            # Directory
            else:
                try:
                    smbclient.mkdir("\\{0}\{1}".format(self.host,remotePath))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        return False
                for root, dirs, files in os.walk(localFile):
                    for dir in dirs:
                        fullPath = os.path.join(root,dir)
                        fullPath=fullPath.replace("/","\\")
                        try:
                            smbclient.mkdir("\\{0}\{1}\{2}".format(self.host,remotePath,fullPath[len(localFile)+1:]))
                        except OSError as e:
                            if e.errno != errno.EEXIST:
                                return False
                    for _file in files:
                        fullPath = os.path.join(root,_file)
                        f = open(fullPath, mode="rb")
                        fullPath=fullPath.replace("/","\\")
                        remoteFile = smbclient.open_file("\\{0}\{1}\{2}".format(self.host,remotePath,fullPath[len(localFile)+1:]), mode="wb",)
                        try:
                            while True:
                                part = f.read(4096)
                                if not part:
                                    break
                                remoteFile.write(part)
                        except:
                            return False
                        finally:
                            remoteFile.close()
                            f.close()
                return True
        return False

    def download(self,remoteFile,localPath):
        if self.smb:
            f = open(localPath, mode="wb")
            try:
                remoteFile = smbclient.open_file("\\{0}\{1}".format(self.host,remoteFile), mode="rb")
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
