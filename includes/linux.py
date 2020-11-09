from paramiko import SSHClient,Transport, RSAKey, AutoAddPolicy
from sshtunnel import SSHTunnelForwarder
from scp import SCPClient
from pathlib import Path
import os

class linux():
    # client = None

    def __init__(self, host, username="root", keyFile='', password='',port_forward=False,port=""):
        self.error          = ""
        self.host           = host
        self.keyFile        = keyFile
        self.username       = username
        self.password       = password
        self.port_forward   = port_forward
        
        if port:
            self.port           = int(port)      
        if not self.port_forward:
            self.scp = self.connectSCP(self.connect())


    def connect(self):
        try:    
            if self.port_forward:
                if self.keyFile != '':
                    print("SSH PORT FORWARD WITH KEY FILE")
                    try:
                        client = SSHTunnelForwarder(
                        (self.host, 22),
                        ssh_pkey=self.keyFile,
                        ssh_username=self.username,
                        ssh_private_key_password=self.password,
                        remote_bind_address=('127.0.0.1', self.port))
                    except Exception as e:
                        print(e)
                else:
                    client = SSHTunnelForwarder(
                    (self.host, 22),
                    ssh_username=self.username,
                    ssh_password=self.password,
                    remote_bind_address=('127.0.0.1', self.port))
            else:
                print("PAMRIKO")
                client = SSHClient()
                client.load_system_host_keys()
                client.set_missing_host_key_policy(AutoAddPolicy())


                if self.keyFile != '':
                    try:
                        # get_key = RSAKey.from_private_key_file(self.keyFile,self.password)
                        # transport = Transport((self.host, 22))                  
                        # transport.get_remote_server_key()
                        # transport.connect(self.host, username=self.username, pkey=get_key)
                        # transport.connect()
                        # transport.close()

                        if self.password:
                            client.connect(self.host, username=self.username, key_filename=self.keyFile,passphrase=self.password, look_for_keys=True, timeout=5000)
                        else:
                            client.connect(self.host, username=self.username, key_filename=self.keyFile, look_for_keys=True, timeout=5000)

                    except Exception as e:
                        print(e)
                else:
                    client.connect(self.host, username=self.username, password=self.password, look_for_keys=True, timeout=5000)

            # print(client.get_transport())
            # client.close()

            return client
        except Exception as e:
            self.error = e
            return None



    def connectSCP(self, client):
        scp = SCPClient(client.get_transport())
        return scp

    def disconnect(self):
        if not self.port_forward:
        # if self.client:
            self.client.close()
            self.client = None

    def reboot(self,timeout):
        # Not implimented yet!
        pass

    def command(self, command, args=[], elevate=False):
        if not self.port_forward:
            client = self.connect()
            #add tear down try, except finally
            if elevate:
                stdin, stdout, stderr = client.exec_command("sudo {0} {1}".format(command, " ".join(args)).strip())
            else:
                stdin, stdout, stderr = client.exec_command("{0} {1}".format(command, " ".join(args)).strip())

            exitCode = stdout.channel.recv_exit_status()
            response = stdout.readlines()
            errors = stderr.readlines()
            return (exitCode, response, errors)

    def start_port_forward(self):
        try:
            client = self.connect()
            client.start()                        

            return client,client.local_bind_port

        except Exception as e:
            print(e)

    def stop_port_forward(self,client):
        try:
            client.stop()

        except Exception as e:
            print(e)

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

    # i'll add the teardown method
    # def __del__(self):
    #     print("disconnect")
    #     self.disconnect()



