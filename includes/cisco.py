from paramiko import SSHClient, AutoAddPolicy, ssh_exception
import time
import jimi

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
            try:
                client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=self.timeout,banner_timeout=200)
            except ssh_exception.SSHException:
                time.sleep(2)
                client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=self.timeout,banner_timeout=200)
            self.channel = client.invoke_shell()
            if not self.recv():
                startTime = time.time()
                detectedDevice = ""
                while ( time.time() - startTime < 5 ):
                    self.command("")
                    if self.channel.recv_ready():
                        detectedDevice += self.channel.recv(2048).decode().strip()
                    time.sleep(0.5)
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

    def recv(self,timeout=5,attempt=0):
        startTime = time.time()
        deviceHostname = self.deviceHostname
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
                elif recvBuffer.split('\n')[-1].lower().startswith(deviceHostname.lower()):
                    result = True
                    break 
            time.sleep(0.1)
        if result:
            return recvBuffer
        elif attempt < 3:
            attempt += 1
            self.channel.send(" ")
            recvData = self.recv(timeout,attempt)
            if recvData:
                recvBuffer += recvData
                return recvBuffer
        return False

    def sendCommand(self,command,attempt=0):
        self.channel.send("{0}{1}".format(command,"\n"))
        time.sleep(0.5)
        return True
        
    def command(self, command, args=[], elevate=False, runAs=None, timeout=5):
        if command == "enable":
            enableResult = self.enable(self.enablePassword)
            if enableResult:
                return (0, enableResult, "")
            else:
                return (None, enableResult, "")
        elif command == "copy running-config startup-config":
            returnedData = ""
            self.sendCommand(command)
            if self.awaitStringRecv("Destination filename [startup-config]?"):
                self.sendCommand("")
                returnedData = self.recv(timeout)
                return (0, returnedData, "")
            else:
                return (None, "", "Unable to save config")
        if args:
            command = command + " " + " ".join(args)
        if self.sendCommand(command):
            returnedData = jimi.helpers.replaceBackspaces(self.recv(timeout))
            if command not in returnedData:
                return (None,returnedData,"Unable to send command")
        else:
            return (None,"","Unable to send command")
        if returnedData == False or "% Invalid input detected at '^'" in returnedData or "% Incomplete command." in returnedData or "Command rejected" in returnedData:
            return (None,"",returnedData)
        return (0, returnedData, "")

    def __del__(self):
        self.disconnect()
