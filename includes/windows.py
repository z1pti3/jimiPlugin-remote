from threading import Lock
from winrm.protocol import Protocol
from winrm.exceptions import WinRMError, WinRMOperationTimeoutError, WinRMTransportError
import smbclient
from pathlib import Path
import os
import time
import errno

# Cheat without using smbclient low level mode to detmine if the client is open for more than one flow
openConnections = {}
openConnectionsLock = Lock()

class windows():

    def __init__(self, host, username="administrator", password=""):
        self.host = host
        self.username = username
        self.password = password
        self.error = ""
        self.client = self.connect(host,username,password)
        if self.client:
            self.smb = self.connectSMB(host,username,password)
        else:
            self.smb = None

    def __del__(self):
        self.disconnect()
        
    def connect(self,host,username,password):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password,read_timeout_sec=30)
        return client

    def connectSMB(self,host,username,password):
        try:
            with openConnectionsLock:
                if host not in openConnections:
                    smbclient.register_session(host, username=username, password=password,connection_timeout=30)
                    openConnections[host] = time.time()
                else:
                    self.error = "Existing connection still active"
                    return False
        except Exception as e:
            self.error = e
            return None
        return True

    def disconnect(self):
        if self.client:
            self.client = None

        with openConnectionsLock:
            if self.host in openConnections:
                del openConnections[self.host]
                smbclient.delete_session(self.host)
                self.smb = None

    def reboot(self,timeout):
        startTime = time.time()
        exitCode, response, error = self.executeCommand("shutdown -r -t 30 -f")
        endTime = time.time()
        while endTime - startTime < timeout:
            endTime = time.time()
            try:
                self.executeCommand("ipconfig")
            except:
                break
            time.sleep(10)
        if exitCode == 0:
            while endTime - startTime < timeout:
                endTime = time.time()
                time.sleep(10)
                self.client = self.connect(self.host,self.username,self.password)
                if self.client:
                    return True
        else:
            self.error = "Unable to reboot server - command failed"
        return False

    def executeCommand(self,command,args=[],elevate=False):
        clientShell = self.client.open_shell()
        commandId = self.client.run_command(clientShell,command, args)
        stdout, stderr, exitCode = self.client.get_command_output(clientShell, commandId)
        self.client.cleanup_command(clientShell, commandId)
        self.client.close_shell(clientShell)
        response = stdout.decode().strip()
        errors = stderr.decode().strip()
        return (exitCode, response, errors)

    def command(self, command, args=[], elevate=False):
        if self.client:
            return self.executeCommand(command,args,elevate)

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
                except Exception as e:
                    self.error = e
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
                        except Exception as e:
                            self.error = e
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
            except Exception as e:
                self.error = e
        return False

