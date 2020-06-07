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
        password = auth.getPasswordFromENC(self.password)
        keyfile = helpers.evalString(self.keyfile,{"data" : data})

        if keyfile != "":
            client = linux.linux(host,user,keyfile=keyfile)
        else:
            client = linux.linux(host,user,password=password)
        if client.client != None:
            persistentData["remote"]={}
            persistentData["remote"]["client"] = client
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            return actionResult

    def setAttribute(self,attr,value):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectLinux, self).setAttribute(attr,value)


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
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
            return actionResult

    def setAttribute(self,attr,value):
        if attr == "password" and not value.startswith("ENC "):
            self.password = "ENC {0}".format(auth.getENCFromPassword(value))
            return True
        return super(_remoteConnectWindows, self).setAttribute(attr,value)


class _remoteCommand(action._action):
    command = str()
    elevate = bool()

    def run(self,data,persistentData,actionResult):
        command = helpers.evalString(self.command,{"data" : data})
        client = None
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                client = persistentData["remote"]["client"]
        if client:
            exitCode, output, errors = client.command(command,elevate=self.elevate)
            actionResult["result"] = True
            actionResult["data"] = output
            actionResult["errors"] = errors
            actionResult["rc"] = exitCode
            return actionResult
        else:
            actionResult["result"] = False
            actionResult["rc"] = 403
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
                actionResult["rc"] = 0
                return actionResult

        actionResult["result"] = False
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
                actionResult["rc"] = 0
                return actionResult
                
        actionResult["result"] = False
        actionResult["rc"] = 403
        return actionResult