from threading import Lock
from winrm.protocol import Protocol
from winrm.exceptions import WinRMError, WinRMOperationTimeoutError, WinRMTransportError
import smbclient
from pathlib import Path
import os
import time
import errno

class windows():

    def __init__(self, host, username="administrator", password=""):
        self.host = host
        self.username = username
        self.password = password
        self.error = ""
        self.client = self.connect(host,username,password)

    def __del__(self):
        pass
        #self.disconnect()
        
    def connect(self,host,username,password):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password,read_timeout_sec=30)
        return client

    def disconnect(self):
        if self.client:
            self.client = None
            smbclient.delete_session(self.host)

    def reboot(self,timeout):
        startTime = time.time()
        exitCode, currentUpTime, error = self.executeCommand("powershell.exe -nop -C \"((get-date) - (gcim Win32_OperatingSystem).LastBootUpTime).TotalSeconds\"")
        if exitCode == None or exitCode != 0:
            self.error = "Unable to get current uptime of system"
            return False
        exitCode, response, error = self.executeCommand("shutdown -r -t 1 -f")  
        if exitCode != None and exitCode == 0:
            newUpTime = currentUpTime
            endTime = time.time()
            while newUpTime >= currentUpTime and endTime - startTime < timeout:
                time.sleep(10)
                endTime = time.time()
                try:
                    self.client = self.connect(self.host,self.username,self.password)
                    if self.client:
                        exitCode, newUpTime, error = self.executeCommand("powershell.exe -nop -C \"((get-date) - (gcim Win32_OperatingSystem).LastBootUpTime).TotalSeconds\"")
                        if exitCode == None or exitCode != 0:
                            newUpTime = currentUpTime
                except:
                    pass
            return True
        else:
            self.error = "Unable to reboot server - command failed"
        return False

    def executeCommand(self,command,args=[],elevate=False):
        try:
            clientShell = self.client.open_shell()
            commandId = self.client.run_command(clientShell,command, args)
            stdout, stderr, exitCode = self.client.get_command_output(clientShell, commandId)
            self.client.cleanup_command(clientShell, commandId)
            self.client.close_shell(clientShell)
            response = stdout.decode().strip()
            errors = stderr.decode().strip()
            return (exitCode, response, errors)
        except Exception as e:
            self.error = e
            return (None, None, None)

    def command(self, command, args=[], elevate=False):
        if self.client:
            return self.executeCommand(command,args,elevate)

    def upload(self,localFile,remotePath):
        smbclient.register_session(self.host, username=self.username, password=self.password, connection_timeout=30)
        # single file
        if not os.path.isdir(localFile):
            try:
                with open(localFile, mode="rb") as f:
                    with smbclient.open_file("\\{0}\{1}".format(self.host,remotePath), mode="wb") as remoteFile:
                        while True:
                            part = f.read(4096)
                            if not part:
                                break
                            remoteFile.write(part)
            except Exception as e:
                self.error = e
                print(e)
                smbclient.delete_session(self.host)
                return False
            smbclient.delete_session(self.host)
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
                    try:
                        fullPath = os.path.join(root,_file)
                        with open(fullPath, mode="rb")as f:
                            fullPath=fullPath.replace("/","\\")
                            with smbclient.open_file("\\{0}\{1}\{2}".format(self.host,remotePath,fullPath[len(localFile)+1:]), mode="wb") as remoteFile:
                                while True:
                                    part = f.read(4096)
                                    if not part:
                                        break
                                    remoteFile.write(part)
                    except Exception as e:
                        self.error = e
                        smbclient.delete_session(self.host)
                        return False
            smbclient.delete_session(self.host)
            return True
        return False

    def download(self,remoteFile,localPath):
        smbclient.register_session(self.host, username=self.username, password=self.password,connection_timeout=30)
        try:
            with open(localPath, mode="wb") as f:
                with smbclient.open_file("\\{0}\{1}".format(self.host,remoteFile), mode="rb") as remoteFile:
                    while True:
                        part = remoteFile.read(4096)
                        if not part:
                            break
                        f.write(part)
            smbclient.delete_session(self.host)
            return True
        except Exception as e:
            self.error = e
            smbclient.delete_session(self.host)
        return False

