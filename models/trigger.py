import re
import time

from core import auth, db
from core.models import trigger

from plugins.remote.includes import windows

class _remotePullWinEvents(trigger._trigger):
    server = str()
    eventName = "Security"
    username = str()
    password = str()
    lastPull = int()
    maxEvents = 1000

    def check(self):
        password = auth.getPasswordFromENC(self.password)
        client = windows.windows(self.server,self.username,password)
        now = int(time.time())
        command = "powershell.exe -C \"Get-WinEvent -FilterHashtable @{Logname='"+self.eventName+"'} -MaxEvents "+str(self.maxEvents)+" -oldest | ForEach-Object { '<345start768>';($_ | format-list);'<678end546>' };\""
        if self.lastPull > 0:
            command = "powershell.exe -C \"Get-WinEvent -FilterHashtable @{Logname='"+self.eventName+"';'startTime'=((Get-Date 01.01.1970)+([System.TimeSpan]::fromseconds("+str(self.lastPull)+")))} -MaxEvents "+str(self.maxEvents)+" -oldest | ForEach-Object { '<345start768>';($_ | format-list);'<678end546>' };\""
        exitCode, stdout, stderr = client.command(command)
        client.disconnect()
        events = re.findall(r'(<345start768>[\W\w\D\r\n]*?<678end546>)',stdout,re.MULTILINE)
        self.result["events"] = events
        self.lastPull = now
        self.update(["lastPull"])

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "password" and not value.startswith("ENC "):
            if db.fieldACLAccess(sessionData,self.acl,attr,accessType="write"):
                self.password = "ENC {0}".format(auth.getENCFromPassword(value))
                return True
            return False
        return super(_remotePullWinEvents, self).setAttribute(attr,value,sessionData)

