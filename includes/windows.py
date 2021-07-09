from threading import Lock
import winrm
from winrm.protocol import Protocol
from winrm.exceptions import WinRMError, WinRMOperationTimeoutError, WinRMTransportError
import smbclient
from pathlib import Path
import os
import time
import errno
from pypsexec.client import Client

from plugins.remote.includes import remote

class windowsPSExec(remote.remote):

    def __init__(self, host, username="administrator", password="", encrypt=True):
        self.host = host
        self.username = username
        self.password = password
        self.error = ""
        self.type = "windowsPSExec"
        self.client = self.connect(host,username,password,encrypt)

    def __del__(self):
        self.disconnect()
        
    def connect(self,host,username,password,encrypt):
        client = Client(host, username=username, password=password, encrypt=encrypt)
        client.connect()
        client.create_service()
        return client

    def disconnect(self):
        if self.client:
            self.client.remove_service()
            self.client.disconnect()
            self.client = None

    def command(self, command, args=[], elevate=False, runAs=None, timeout=30):
        if self.client:
            if runAs == "SYSTEM":
                response, errors, exitCode = self.client.run_executable(command, arguments=" ".join(args), use_system_account=True, timeout_seconds=timeout)
            else:
                response, errors, exitCode = self.client.run_executable(command, arguments=" ".join(args), timeout_seconds=timeout)
            return (exitCode, response, errors)

class windows(remote.remote):

    def __init__(self, host, username="administrator", password="", smb=True):
        self.host = host
        self.username = username
        self.password = password
        self.error = ""
        self.type = "windows"
        self.client = self.connect(host,username,password,smb)

    def __del__(self):
        self.disconnect()
        
    def connect(self,host,username,password,smb):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password,read_timeout_sec=30)
        if smb:
            try:
                smbclient.register_session(self.host, username=self.username, password=self.password, connection_timeout=30)
            except Exception as e:
                self.error = str(e)
                return None
        return client

    def disconnect(self):
        if self.client:
            self.client = None
            #smbclient.delete_session(self.host)

    def reboot(self,timeout):
        startTime = time.time()
        exitCode, currentUpTime, error = self.executeCommand("powershell.exe -nop -C \"((get-date) - (gcim Win32_OperatingSystem).LastBootUpTime).TotalSeconds\"")
        if exitCode == None or exitCode != 0:
            self.error = "Unable to get current uptime of system"
            return False
        exitCode, response, error = self.executeCommand("shutdown -r -t 1 -f")  
        if exitCode != None and exitCode == 0:
            newUpTime = currentUpTime
            endTime = time.time()
            while newUpTime >= currentUpTime and endTime - startTime < timeout:
                time.sleep(10)
                endTime = time.time()
                try:
                    self.client = self.connect(self.host,self.username,self.password)
                    if self.client:
                        exitCode, newUpTime, error = self.executeCommand("powershell.exe -nop -C \"((get-date) - (gcim Win32_OperatingSystem).LastBootUpTime).TotalSeconds\"")
                        if exitCode == None or exitCode != 0:
                            newUpTime = currentUpTime
                except:
                    pass
            return True
        else:
            self.error = "Unable to reboot server - command failed"
        return False

    # Timeout not implemented
    def executeCommand(self,command,args=[],elevate=False,runAs=None,timeout=300):
        try:
            if runAs:
                if runAs == "user":
                    if args:
                        command = command + " ".join(args)
                        command = "{0}\nrm c:\\windows\\temp\\jimiRunAsUser.ps1".format(powershellRunAsLoggedInUser.replace("<CMD>",command))
                    else:
                        command = "{0}\nrm c:\\windows\\temp\\jimiRunAsUser.ps1".format(powershellRunAsLoggedInUser.replace("<CMD>",command))
                    with smbclient.open_file("\\{0}\{1}".format(self.host,"c$\\windows\\temp\\jimiRunAsUser.ps1"), mode="wb") as remoteFile:
                        for line in command.split("\n"):
                            remoteFile.write("{0}\n".format(line).encode())
                    clientShell = self.client.open_shell()
                    commandId = self.client.run_command(clientShell,"powershell.exe -noProfile -ExecutionPolicy Bypass -File c:\\windows\\temp\\jimiRunAsUser.ps1")
                    stdout, stderr, exitCode = self.client.get_command_output(clientShell, commandId)
                    self.client.cleanup_command(clientShell, commandId)
                    self.client.close_shell(clientShell)
                    response = stdout.decode().strip()
                    errors = stderr.decode().strip()
                    return (exitCode, response, errors)
            else:
                clientShell = self.client.open_shell()
                commandId = self.client.run_command(clientShell,command, args)
                stdout, stderr, exitCode = self.client.get_command_output(clientShell, commandId)
                self.client.cleanup_command(clientShell, commandId)
                self.client.close_shell(clientShell)
                response = stdout.decode().strip()
                errors = stderr.decode().strip()
                return (exitCode, response, errors)
        except Exception as e:
            self.error = str(e)
        return (None, None, None)

    # Timeout not implimented yet
    def command(self, command, args=[], elevate=False, runAs=None, timeout=300):
        if self.client:
            return self.executeCommand(command,args,elevate,runAs,timeout)

    def upload(self,localFile,remotePath):
        # single file
        if not os.path.isdir(localFile):
            try:
                with open(localFile, mode="rb") as f:
                    with smbclient.open_file("\\{0}\{1}".format(self.host,remotePath), mode="wb") as remoteFile:
                        while True:
                            part = f.read(4096)
                            if not part:
                                break
                            remoteFile.write(part)
            except Exception as e:
                self.error = str(e)
                return False
            return True
        # Directory
        else:
            try:
                smbclient.mkdir("\\{0}\{1}".format(self.host,remotePath))
            except OSError as e:
                if e.errno != errno.EEXIST:
                    return False
            for root, dirs, files in os.walk(localFile):
                for dir in dirs:
                    fullPath = os.path.join(root,dir)
                    fullPath=fullPath.replace("/","\\")
                    try:
                        smbclient.mkdir("\\{0}\{1}\{2}".format(self.host,remotePath,fullPath[len(localFile)+1:]))
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            return False
                for _file in files:
                    try:
                        fullPath = os.path.join(root,_file)
                        with open(fullPath, mode="rb")as f:
                            fullPath=fullPath.replace("/","\\")
                            with smbclient.open_file("\\{0}\{1}\{2}".format(self.host,remotePath,fullPath[len(localFile)+1:]), mode="wb") as remoteFile:
                                while True:
                                    part = f.read(4096)
                                    if not part:
                                        break
                                    remoteFile.write(part)
                    except Exception as e:
                        self.error = str(e)
                        return False
            return True
        return False

    def download(self,remoteFile,localPath,createMissingFolders):
        try:
            if createMissingFolders:
                splitChar = "\\"
                if splitChar not in localPath:
                    splitChar = "/"
                if not os.path.isdir(localPath.rsplit(splitChar,1)[0]):
                    os.makedirs(localPath.rsplit(splitChar,1)[0])
            with open(localPath, mode="wb") as f:
                with smbclient.open_file("\\{0}\{1}".format(self.host,remoteFile), mode="rb") as remoteFile:
                    while True:
                        part = remoteFile.read(4096)
                        if not part:
                            break
                        f.write(part)
            return True
        except Exception as e:
            self.error = str(e)
        return False

powershellRunAsLoggedInUser = """
$user = WMIC COMPUTERSYSTEM GET USERNAME | Select-String \"\\\\\"; $username = $user.line.split(\"\\\")[1]; $user = $user.line.trim(); $usersid = (New-Object -ComObject Microsoft.DiskQuota).TranslateLogonNameToSID((Get-WmiObject -Class Win32_ComputerSystem).Username) ; $userprofile = gwmi win32_userprofile | select localpath, sid |  Where-Object {$_.sid -eq $usersid}; $userprofilepath = $userprofile.localpath ;$random = get-random ; schtasks /create /st 23:59 /ru $user /f /tn \"$random\" /sc once /tr \"cmd /c <CMD> >> $userprofilepath\\appdata\\local\\temp\\$random.txt 2>&1  & echo $random >> $userprofilepath\\appdata\\local\\temp\\$random.txt\"; schtasks /run /tn \"$random\" | Out-Null; $a = 0; $taskresultdata = ((schtasks.exe /query /tn \"$random\" /v /fo CSV | ConvertFrom-Csv | Select-Object) 2> $null); while (($taskresultdata.\"Last Run Time\" -eq \"N/A\" -or $taskresultdata.\"Last Run Time\" -eq $null -or $taskresultdata.\"Last Run Time\" -eq \"30/11/1999 00:00:00\" -or $taskresultdata.\"Status\" -ne \"Ready\") -and ($a -lt 120)){Start-Sleep 1; $a = $a + 1; $taskresultdata = ((schtasks.exe /query /tn \"$random\" /v /fo CSV | ConvertFrom-Csv | Select-Object) 2> $null)};write-host \"Out of schtasks run check!\";$filetocheck = $userprofilepath+\"\\appdata\\local\\temp\\\"+$random+\".txt\"; $fileExists = (Test-Path $fileToCheck -PathType leaf); while (($fileExists -eq $False) -and ($a -lt 60)){Start-Sleep 1; $a = $a + 1; write-host $a; $fileExists = (Test-Path $fileToCheck -PathType leaf)};$result = (Get-Content $userprofilepath\\appdata\\local\\temp\\$random.txt | %{$_ -match \"$random\"});while (($result[$result.count -1] -eq $False) -and ($a -lt 60)){Start-Sleep 1; write-host $a; $result = (Get-Content $userprofilepath\\appdata\\local\\temp\\$random.txt | %{$_ -match \"$random\"});write-host $result[$result.count -1];$a = $a + 1};write-host \"Out of EOF check!\"; type $userprofilepath\\appdata\\local\\temp\\$random.txt;start-sleep 1;rm $userprofilepath\\appdata\\local\\temp\\$random.txt;schtasks /delete /f /tn $random
"""

