from paramiko import SSHClient, AutoAddPolicy
import time
import re
import logging

from plugins.remote.includes import remote

class cisco(remote.remote):

    def __init__(self, host, deviceHostname, username="Admin", password='', enablePassword="", port=22, timeout=5):
        self.host = host
        self.deviceHostname = deviceHostname
        self.timeout = timeout
        self.enablePassword = enablePassword
        self.error = "" 
        self.type = "cisco"
        self.client = self.connect(username,password,port)

    def connect(self,username,password,port):
        try: 
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())   
            client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=self.timeout)
            self.channel = client.invoke_shell()
            detectedDevice = self.channel.recv(len(self.deviceHostname)+2).decode().strip()
            if detectedDevice != self.deviceHostname:
                self.error = f"Device detected name does not match the device name provided. Hostname found = {detectedDevice}"
                client.close()
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

    def awaitStringRecv(self,awaitString,timeout=5):
        startTime = time.time()
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < timeout ):
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

    def recv(self,timeout=5):
        startTime = time.time()
        deviceHostname = self.deviceHostname()
        if len(deviceHostname) >= 20:
            deviceHostname = deviceHostname[:20]
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < timeout ):
            if self.channel.recv_ready():
                recvBuffer += self.channel.recv(1024).decode().strip()
                if recvBuffer.split('\n')[-1].endswith("--More--"):
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-8]
                elif recvBuffer.split('\n')[-1].startswith(deviceHostname):
                    result = True
                    break 
            time.sleep(0.1)
        if result:
            return recvBuffer
        return False

    def sendCommand(self,command,attempt=0):
        if attempt > 3:
            return False
        sentBytes = self.channel.send("{0}{1}".format(command,"\n"))
        recvBuffer = ""
        startTime = time.time()
        while time.time() - startTime < 5:
            recvBuffer += self.channel.recv(sentBytes-len(recvBuffer.encode())).decode()
            if command in recvBuffer:
                return True
            time.sleep(0.1)
        logging.warning("Command was not received by remote console. command={0}, attempt={1}".format(command),attempt)
        return self.sendCommand(command,attempt+1)
        
    def command(self, command, args=[], elevate=False, runAs=None, timeout=5):
        if command == "enable":
            return (0, self.enable(self.enablePassword), "")
        if args:
            command = command + " " + " ".join(args)
        if self.sendCommand(command):
            returnedData = self.recv(timeout)
        else:
            return (None,"","Unable to send command")
        if returnedData == False or "% Invalid input detected at '^'" in returnedData or "% Incomplete command." in returnedData or "Command rejected" in returnedData:
            return (None,"",returnedData)
        return (0, returnedData, "")

    def __del__(self):
        self.disconnect()
