from paramiko import SSHClient,Transport, RSAKey, AutoAddPolicy
from sshtunnel import SSHTunnelForwarder
from scp import SCPClient
from pathlib import Path
import os
import time

class linux():
    # client = None

    def __init__(self, host, username="root", keyFile='', password='',port_forward=False,port="",timeout=10):
        self.error          = ""
        self.host           = host
        self.keyFile        = keyFile
        self.username       = username
        self.password       = password
        self.port_forward   = port_forward
        self.type = "linux"
        
        if port:
            self.port           = int(port)     

        if not self.port_forward:
            if self.keyFile != '':
                self.client = self.connect(self.host,self.username,keyFile=self.keyFile,password=self.password,timeout=timeout)
            else:
                self.client = self.connect(self.host,self.username,password=self.password,timeout=timeout)          
        else:
            if keyFile != '':
                self.client,self.sshTunnel = self.connect(self.host,self.username,keyFile=self.keyFile,password=self.password,port_forward=self.port_forward,port=self.port,timeout=timeout)
                
                self.tunnelPort = self.sshTunnel.local_bind_port
                # print(f"Binded init port is {self.tunnelPort}")
            else:
                self.client,self.sshTunnel = self.connect(self.host,self.username,keyFile=self.keyFile,port_forward=self.port_forward,port=self.port,timeout=timeout)
        
        if self.client:
            self.scp    = self.connectSCP(self.client)

    def connect(self,host,username,keyFile="",password='',port_forward=False,port="",timeout=10):
        try: 
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())                    
            if self.port_forward:       
                if self.keyFile != '':
                    try:  
                        if password != "":
                            client.connect(host, username=username, key_filename=keyFile,passphrase=password, look_for_keys=True, timeout=timeout)
                        else:
                            client.connect(host, username=username, key_filename=keyFile, look_for_keys=True, timeout=timeout)
                        
                        sshTunnel = SSHTunnelForwarder(
                        (host, 22),
                        ssh_pkey=keyFile,
                        ssh_username=username,
                        ssh_private_key_password=password,
                        remote_bind_address=('127.0.0.1', port))
                    except Exception as e:
                        self.error = e
                        return None
                else:
                    sshTunnel = SSHTunnelForwarder(
                    (host, 22),
                    ssh_username=username,
                    ssh_password=password,
                    remote_bind_address=('127.0.0.1', port))

                    client.connect(host, username=username, password=password, look_for_keys=True, timeout=10)
                
                sshTunnel.start()
                return client,sshTunnel
            else:
                if keyFile != '':
                    try:
                        if password != "":
                            client.connect(host, username=username, key_filename=keyFile, passphrase=password, look_for_keys=True, timeout=10)
                        else:
                            client.connect(host, username=username, key_filename=keyFile, look_for_keys=True, timeout=10)

                    except Exception as e:
                        self.error = e
                        return None
                else:
                    client.connect(host, username=username, password=password, look_for_keys=True, timeout=10)

                return client
        except Exception as e:
            self.error = e
            return None

    def connectSCP(self, client):
        scp = SCPClient(client.get_transport())
        return scp

    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
        if self.port_forward:
            self.sshTunnel.stop()
            self.sshTunnel = None

    def reboot(self,timeout):
        # Not implimented yet!
        pass

    def command(self, command, args=[], elevate=False, runAs=None, timeout=300):
        if self.client:
            if timeout == 0:
                timeout = 300
            try:
                if elevate:
                    stdin, stdout, stderr = self.client.exec_command("sudo {0} {1}".format(command, " ".join(args)).strip(),timeout=timeout)
                elif runAs:
                    stdin, stdout, stderr = self.client.exec_command("sudo -u {0} {1} {2}".format(runAs,command, " ".join(args)).strip(),timeout=timeout)
                else:
                    stdin, stdout, stderr = self.client.exec_command("{0} {1}".format(command, " ".join(args)).strip(),timeout=timeout)
                response=[]
                while not stdout.channel.exit_status_ready():
                    if stdout.channel.recv_ready():
                        response += stdout.readlines()
                    else:
                        time.sleep(0.25)
                response += stdout.readlines()
                response = "".join(response)
                errors = stderr.readlines()
                exitCode = stdout.channel.recv_exit_status() # Cant be killed by system exit exception
                return (exitCode, response, errors)
            except Exception as e:
                return (503, "", "{0}".format(e))

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



