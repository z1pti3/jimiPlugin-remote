import time
import re
import logging
from netmiko import ConnectHandler

from plugins.remote.includes import remote

class cisco(remote.remote):

    def __init__(self, host, deviceHostname, username="Admin", password='', enablePassword="", port=22, timeout=5):
        self.host = host
        self.deviceHostname = deviceHostname
        self.timeout = timeout
        self.enablePassword = enablePassword
        self.error = "" 
        self.type = "cisco_ios"
        self.client = self.connect(username,password,port)

    def connect(self,username,password,port):
        try: 
            client = ConnectHandler(host=self.host, device_type=self.type, username=username, password=password, secret=self.enablePassword, port=port, system_host_keys=True, timeout=self.timeout)
            detectedDevice = client.find_prompt().strip()[:-1]
            if detectedDevice != self.deviceHostname:
                self.error = f"Device detected name does not match the device name provided. Hostname found = {detectedDevice}"
                client.disconnect()
                return None
            return client
        except Exception as e:
            self.error = e
            return None
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
            self.client = None

    def sendCommand(self,command,attempt=0):
        if attempt > 3:
            return False
        output = self.client.send_command(command)
        if output:
            return output
        time.sleep(0.1)
        logging.warning("Command was not received by remote console. command={0}, attempt={1}".format(command),attempt)
        return self.sendCommand(command,attempt+1)
        
    def command(self, command, args=[], elevate=False, runAs=None, timeout=5):
        if command == "enable":
            try:
                self.client.enable()
                return (0, "test")
            except ValueError:
                return (None,"","Could not enable")
        if args:
            command = command + " " + " ".join(args)
        returnedData = self.sendCommand(command)
        if returnedData is False:
            return (None,"","Unable to send command")
        if returnedData == False or "% Invalid input detected at '^'" in returnedData or "% Incomplete command." in returnedData or "Command rejected" in returnedData:
            return (None,"",returnedData)
        return (0, returnedData, "")

    def __del__(self):
        self.disconnect()