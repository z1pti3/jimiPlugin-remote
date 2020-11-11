from core import settings, helpers, auth
from core.models import action
from plugins.remote.includes import linux, windows

class _remoteConnectLinux(action._action):
    host = str()
    user = str()
    keyfile = str()
    password = str()

    def run(self,data,persistentData,actionResult):
        host = helpers.evalString(self.host,{"data" : data})
        user = helpers.evalString(self.user,{"data" : data})
        if self.password.startswith("ENC"):
            password = auth.getPasswordFromENC(self.password)
        keyfile = helpers.evalString(self.keyfile,{"data" : data})

        if keyfile != "":
            client = linux.linux(host,user,keyFile=keyfile)
        else:
            client = linux.linux(host,user,password=password)
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
        return super(_remoteConnectLinux, self).setAttribute(attr,value,sessionData=sessionData)


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

    def run(self,data,persistentData,actionResult):
        command = helpers.evalString(self.command,{"data" : data})
        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            exitCode, output, errors = client.command(command,elevate=self.elevate,runAs=self.runAs)
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

    def run(self,data,persistentData,actionResult):
        remoteFile = helpers.evalString(self.remoteFile,{"data" : data})
        localFile = helpers.evalString(self.localFile,{"data" : data})

        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            if client.download(remoteFile,localFile):
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