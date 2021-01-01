from core import settings, helpers, auth
from core.models import action
from plugins.remote.includes import linux, windows

class _remoteConnectLinux(action._action):
    host = str()
    user = str()
    keyfile = str()
    password = str()
    isPortForward = bool()
    port_forward = str()
    

    def run(self,data,persistentData,actionResult):
        host    = helpers.evalString(self.host,{"data" : data})
        user    = helpers.evalString(self.user,{"data" : data})
        port    = helpers.evalString(self.port_forward,{"data" : data})
        if self.password.startswith("ENC"):
            password = auth.getPasswordFromENC(self.password)
        else:
            password = ""
        keyfile = helpers.evalString(self.keyfile,{"data" : data})

        if self.isPortForward:
            if keyfile != "":
                if password:
                    client= linux.linux(host,user,keyFile=keyfile,password=password,port_forward=True,port=port)
                else:
                    client = linux.linux(host,user,keyFile=keyfile,port_forward=True,port=port)
            else:
                client = linux.linux(host,user,password=password)
        else:
            if keyfile != "":
                if password != "":
                    client = linux.linux(host,user,keyFile=keyfile,password=password)
                else:
                    client = linux.linux(host,user,keyFile=keyfile)
            else:
                client = linux.linux(host,user,password=password)

        if client.client != None:
            persistentData["remote"]={}
            persistentData["remote"]["client"] = client

            if self.isPortForward:
                # print(f"MAIN port is {client.tunnelPort}")
                persistentData["remote"]["port"] = client.tunnelPort
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["msg"] = "Connection successful"
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "Connection failed - {0}".format(client.error)
            return actionResult

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectLinux, self).setAttribute(attr,value,sessionData=sessionData)

class _remoteLinuxStartPortForward(action._action):

    def run(self,data,persistentData,actionResult):

        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
    
        if client:       
            print("Starting Connection")            
            test,port = client.start_port_forward()

            persistentData["remote"]["port"] = port
            persistentData["remote"]["portForwardStatus"] = True
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["portForwardStatus"] = True

        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "No connection found"
            return actionResult


class _remoteLinuxStopPortForward(action._action):

    def run(self,data,persistentData,actionResult):

        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
            if "port" in persistentData["remote"]:
                port = persistentData["remote"]["port"]
        if client and port:
            print("Stopping Connection")       
            client.stop_port_forward(client)
            actionResult["result"] = True
            actionResult["rc"] = 0
            persistentData["remote"]["portForwardStatus"] = False

        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "No connection found"
            return actionResult


class _remoteConnectWindows(action._action):
    host = str()
    user = str()
    password = str()

    def run(self,data,persistentData,actionResult):
        host = helpers.evalString(self.host,{"data" : data})
        user = helpers.evalString(self.user,{"data" : data})
        password = auth.getPasswordFromENC(self.password)

        client = windows.windows(host,user,password)
        if client.client != None:
            persistentData["remote"]={}
            persistentData["remote"]["client"] = client
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["msg"] = "Connection successful"
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "Connection failed - {0}".format(client.error)
            return actionResult

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectWindows, self).setAttribute(attr,value,sessionData=sessionData)

class _remoteDisconnect(action._action):
    def run(self,data,persistentData,actionResult):
        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            client.disconnect()
        actionResult["result"] = True
        actionResult["msg"] = "Connection disconnected"
        actionResult["rc"] = 0
        return actionResult

class _remoteCommand(action._action):
    command = str()
    elevate = bool()
    runAs = str()
    timeout = 300

    def run(self,data,persistentData,actionResult):
        command = helpers.evalString(self.command,{"data" : data})
        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            exitCode, output, errors = client.command(command,elevate=self.elevate,runAs=self.runAs,timeout=self.timeout)
            
            if exitCode != None:
                actionResult["result"] = True
                actionResult["data"] = output
                actionResult["errors"] = errors
                actionResult["rc"] = exitCode
                return actionResult
            else:
                actionResult["result"] = False
                actionResult["msg"] = client.error
                actionResult["data"] = ""
                actionResult["errors"] = ""
                actionResult["rc"] = 255
                return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "No connection found"
            return actionResult

class _remoteReboot(action._action):
    timeout = int()

    def run(self,data,persistentData,actionResult):
        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            timeout = 60
            if self.timeout > 0:
                timeout = self.timeout
            result = client.reboot(timeout)
            actionResult["result"] = result
            if result:
                actionResult["rc"] = 0
                actionResult["msg"] = "Reboot successful"
            else:
                actionResult["rc"] = 255
                actionResult["msg"] = "Reboot failed"
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            actionResult["msg"] = "No connection found"
            return actionResult

class _remoteDownload(action._action):
    remoteFile = str()
    localFile = str()
    createMissingFolders = bool()

    def run(self,data,persistentData,actionResult):
        remoteFile = helpers.evalString(self.remoteFile,{"data" : data})
        localFile = helpers.evalString(self.localFile,{"data" : data})

        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            if client.download(remoteFile,localFile,self.createMissingFolders):
                actionResult["result"] = True
                actionResult["msg"] = "File transfered successful"
                actionResult["rc"] = 0
                return actionResult

        actionResult["result"] = False
        actionResult["msg"] = "File transfer failed"
        actionResult["rc"] = 403
        return actionResult

class _remoteUpload(action._action):
    remoteFile = str()
    localFile = str()

    def run(self,data,persistentData,actionResult):
        remoteFile = helpers.evalString(self.remoteFile,{"data" : data})
        localFile = helpers.evalString(self.localFile,{"data" : data})

        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            if client.upload(localFile,remoteFile):
                actionResult["result"] = True
                actionResult["msg"] = "File transfered successful"
                actionResult["rc"] = 0
                return actionResult
                
        actionResult["result"] = False
        actionResult["msg"] = "File transfer failed"
        actionResult["rc"] = 403
        return actionResult