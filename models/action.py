from core import settings, helpers, auth
from core.models import action
from plugins.remote.includes import linux, windows, fortigate

import jimi

class _remoteConnectLinux(action._action):
    host = str()
    user = str()
    keyfile = str()
    password = str()
    isPortForward = bool()
    port_forward = str()
    
    def doAction(self,data):
        host    = helpers.evalString(self.host,{"data" : data["flowData"]})
        user    = helpers.evalString(self.user,{"data" : data["flowData"]})
        port    = helpers.evalString(self.port_forward,{"data" : data["flowData"]})
        if self.password.startswith("ENC"):
            password = auth.getPasswordFromENC(self.password)
        else:
            password = ""
        keyfile = helpers.evalString(self.keyfile,{"data" : data["flowData"]})

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
            data["eventData"]["remote"]={}
            data["eventData"]["remote"]["client"] = client

            if self.isPortForward:
                data["eventData"]["remote"]["port"] = client.tunnelPort
            return {"result" : True, "rc" : 0, "msg" : "Connection successful"}
        else:
            return {"result" : False, "rc" : 403, "msg" : "Connection failed - {0}".format(client.error)}

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectLinux, self).setAttribute(attr,value,sessionData=sessionData)

class _remoteLinuxStartPortForward(action._action):

    def doAction(self,data):
        try:
            client = data["eventData"]["remote"]["client"]
        except KeyError:
            client = None

        if client:                
            test,port = client.start_port_forward()
            data["eventData"]["remote"]["port"] = port
            data["eventData"]["remote"]["portForwardStatus"] = True
            return {"result" : True, "rc" : 0, "msg" : "Port forwarding started", "portForwardStatus" : True}
        else:
            return {"result" : False, "rc" : 403, "msg" : "No connection found"}

class _remoteLinuxStopPortForward(action._action):

    def doAction(self,data):
        try:
            client = data["eventData"]["remote"]["client"]
            port = data["eventData"]["remote"]["port"]
        except KeyError:
            client = None
            port = None

        if client and port:    
            client.stop_port_forward(client)
            data["eventData"]["remote"]["portForwardStatus"] = False
            return {"result" : True, "rc" : 0, "msg" : "Port forwarding stopped"}
        else:
            return {"result" : False, "rc" : 403, "msg" : "No connection found"}

class _remoteConnectWindows(action._action):
    host = str()
    user = str()
    password = str()

    def doAction(self,data):
        host = helpers.evalString(self.host,{"data" : data["flowData"]})
        user = helpers.evalString(self.user,{"data" : data["flowData"]})
        password = auth.getPasswordFromENC(self.password)

        client = windows.windows(host,user,password)
        if client.client != None:
            data["eventData"]["remote"]={"client" : client}
            return {"result" : True, "rc" : 0, "msg" : "Connection successful"}
        else:
            return {"result" : False, "rc" : 403, "msg" : "Connection failed - {0}".format(client.error)}

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectWindows, self).setAttribute(attr,value,sessionData=sessionData)

class _remoteConnectFortigate(action._action):
    host = str()
    port = str()
    deviceHostname = str()
    user = str()
    password = str()
    maxRecvTime = 5

    def doAction(self,data):
        host = helpers.evalString(self.host,{"data" : data["flowData"]})
        port = helpers.evalString(self.port,{"data" : data["flowData"]})
        deviceHostname = helpers.evalString(self.deviceHostname,{"data" : data["flowData"]})
        user = helpers.evalString(self.user,{"data" : data["flowData"]})
        if self.password.startswith("ENC"):
            password = auth.getPasswordFromENC(self.password)
        else:
            password = ""

        client = fortigate.fortigate(host,deviceHostname,user,password=password,port=port,maxRecvTime=self.maxRecvTime)

        if client.client != None:
            data["eventData"]["remote"]={"client" : client}
            return {"result" : True, "rc" : 0, "msg" : "Connection successful"}
        else:
            return {"result" : False, "rc" : 403, "msg" : "Connection failed - {0}".format(client.error)}

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectFortigate, self).setAttribute(attr,value,sessionData=sessionData)

class _remoteDisconnect(action._action):
    def doAction(self,data):
        try:
            client = data["eventData"]["remote"]["client"]
        except KeyError:
            client = None
        if client:
            client.disconnect()
        return {"result" : True, "rc" : 0, "msg" : "Connection disconnected"}

class _remoteCommand(action._action):
    command = str()
    elevate = bool()
    runAs = str()
    timeout = 300

    def doAction(self,data):
        command = helpers.evalString(self.command,{"data" : data["flowData"]})
        try:
            client = data["eventData"]["remote"]["client"]
        except KeyError:
            client = None
        if client:
            exitCode, output, errors = client.command(command,elevate=self.elevate,runAs=self.runAs,timeout=self.timeout)
            
            if exitCode != None:
                return {"result" : True, "rc" : exitCode, "msg" : "Command succesfull", "data" : output, "errors" : errors}
            else:
                return {"result" : False, "rc" : 255, "msg" : client.error, "data" : "", "errors" : ""}
        else:
            return {"result" : False, "rc" : 403, "msg" : "No connection found"}

class _remoteReboot(action._action):
    timeout = int()

    def doAction(self,data):
        try:
            client = data["eventData"]["remote"]["client"]
        except KeyError:
            client = None
        if client:
            timeout = 60
            if self.timeout > 0:
                timeout = self.timeout
            result = client.reboot(timeout)
            if result:
                return {"result" : True, "rc" : 0, "msg" : "Reboot successful"}
            else:
                return {"result" : False, "rc" : 255, "msg" : "Reboot failed"}
        else:
            return {"result" : False, "rc" : 403, "msg" : "No connection found"}

class _remoteDownload(action._action):
    remoteFile = str()
    localFile = str()
    createMissingFolders = bool()
    useStorage = bool()

    def doAction(self,data):
        remoteFile = helpers.evalString(self.remoteFile,{"data" : data["flowData"]})
        localFile = helpers.evalString(self.localFile,{"data" : data["flowData"]})

        if self.useStorage:
            try:
                localFileClass = jimi.storage._storage().getAsClass(query={ "fileData" : localFile, "systemStorage" : True, "source" : "remoteDownload" })[0]
            except:
                localFileClass = jimi.storage._storage()
                localFileClass.new(self.acl,"remoteDownload",localFile,True)
            localFile = localFileClass.getFullFilePath()

        client = None
        if "remote" in data["eventData"]:
            if "client" in data["eventData"]["remote"]:
                client = data["eventData"]["remote"]["client"]
        if client:
            if client.download(remoteFile,localFile,self.createMissingFolders):
                if self.useStorage:
                    localFileClass.calculateHash()
                return {"result" : True, "rc" : 0, "msg" : "File transfered successful"}

        return {"result" : False, "rc" : 403, "msg" : "File transfer failed - {0}".format(client.error)}

class _remoteUpload(action._action):
    remoteFile = str()
    localFile = str()
    useStorage = bool()

    def doAction(self,data):
        remoteFile = helpers.evalString(self.remoteFile,{"data" : data["flowData"]})
        localFile = helpers.evalString(self.localFile,{"data" : data["flowData"]})

        if self.useStorage:
            try:
                localFile = jimi.storage._storage().getAsClass(id=localFile)[0].getLocalFilePath()
            except:
                return {"result" : False, "rc" : 404, "msg" : "Local file not found within storage store. storageID={0}".format(localFile)}

        try:
            client = data["eventData"]["remote"]["client"]
        except KeyError:
            client = None
        if client:
            if client.upload(localFile,remoteFile):
                return {"result" : True, "rc" : 0, "msg" : "File transfered successful"}
        return {"result" : False, "rc" : 403, "msg" : "File transfer failed - {0}".format(client.error)}