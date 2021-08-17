from paramiko import SSHClient, AutoAddPolicy
import time
import re
import logging

from plugins.remote.includes import remote

class fortigate(remote.remote):

    def __init__(self, host, deviceHostname, username="admin", password='', port=22, timeout=5):
        self.host = host
        self.deviceHostname = deviceHostname.lower()
        self.port = port
        self.timeout = timeout
        self.error = ""  
        self.type = "fortigate"

        self.client = self.connect(self.host, username, password)  

    def connect(self,host,username,password):
        try: 
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())   
            client.connect(host, username=username, password=password, port=self.port, look_for_keys=True, timeout=self.timeout)
            self.channel = client.invoke_shell()
            detectedDevice = self.channel.recv(len(self.deviceHostname)+2).decode().strip().lower()
            if detectedDevice != "{0} #".format(self.deviceHostname) and detectedDevice != "{0} $".format(self.deviceHostname):
                self.error = f"Device detected name does not match the device name provided. Hostname found = {detectedDevice}"
                client.close()
                return None
            return client
        except Exception as e:
            self.error = e
            return None

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def recv(self,timeout):
        startTime = time.time()
        recvBuffer = ""
        while ( time.time() - startTime < timeout ):
            if self.channel.recv_ready():
                recvBuffer += self.channel.recv(1024).decode().strip()
                if recvBuffer.split('\n')[-1] == "--More--":
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-8]
                elif re.match(r"^{0} ((#|\$)|\([a-z]+\) (#|\$))$".format(self.deviceHostname) ,recvBuffer.split('\n')[-1].lower()):
                    break 
            time.sleep(0.1)
        return recvBuffer

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
        if args:
            command = command + " " + " ".join(args)
        if self.sendCommand(command):
            returnedData = self.recv(timeout)
        else:
            return (None,"","Unable to send command")
        return (0, returnedData, "")

    def __del__(self):
        self.disconnect()
        
