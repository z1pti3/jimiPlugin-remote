from paramiko import SSHClient, AutoAddPolicy
import time
import re

class cisco():

    def __init__(self, host, deviceHostname, username="Admin", password='', enablePassword="", port=22, maxRecvTime=5):
        self.host = host
        self.deviceHostname = deviceHostname
        self.maxRecvTime = maxRecvTime
        self.enablePassword = enablePassword
        self.error = "" 
        self.type = "cisco"

        self.client = self.connect(username,password,port)

    def connect(self,username,password,port):
        try: 
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())   
            client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=10)
            self.channel = client.invoke_shell()
            detectedDevice = self.channel.recv(len(self.deviceHostname)+2).decode().strip()
            if detectedDevice != self.deviceHostname:
                self.error = "Device detected name does not match the device name provided."
                self.disconnect()
                return None
            return client
        except Exception as e:
            self.error = e
            return None
    
    def enable(self,password):
        self.channel.send("enable\n")
        if self.awaitStringRecv("Password:"):
            self.channel.send("{0}\n".format(password))
            if self.recv():
                return True
        return False

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def awaitStringRecv(self,awaitString):
        startTime = time.time()
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < self.maxRecvTime ):
            if self.channel.recv_ready():
                recvBuffer += self.channel.recv(1024).decode().strip()
                if recvBuffer.split('\n')[-1] == "--More--":
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-8]
                elif recvBuffer.split('\n')[-1].lower().endswith(awaitString.lower()):
                    result = True
                    break
            time.sleep(0.1)
        if result:
            return recvBuffer

        return False

    def recv(self):
        startTime = time.time()
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < self.maxRecvTime ):
            if self.channel.recv_ready():
                recvBuffer += self.channel.recv(1024).decode().strip()
                if recvBuffer.split('\n')[-1].endswith("--More--"):
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-8]
                elif recvBuffer.split('\n')[-1].startswith(self.deviceHostname):
                    result = True
                    break 
            time.sleep(0.1)
        if result:
            return recvBuffer

        return False

    def command(self, command, args=[], elevate=False, runAs=None, timeout=None):
        if command == "enable":
            return (0, self.enable(self.enablePassword), "")
        
        self.channel.send("{0}{1}".format(command,"\n"))
        returnedData = self.recv()
        if returnedData == False or "% Invalid input detected at '^'" in returnedData or "% Incomplete command." in returnedData:
            return (None,"",returnedData)
        return (0, returnedData, "")

    def reboot(self,timeout):
        # Not implimented yet!
        self.error = "Not implimented"
        pass

    def upload(self, localFile, remotePath):
        # Not supported!
        self.error = "Not supported"
        return False

    def download(self, remoteFile, localPath, createMissingFolders):
        # Not supported!
        self.error = "Not supported"
        return False

    def __del__(self):
        self.disconnect()
