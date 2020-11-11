from threading import Lock
import winrm
from winrm.protocol import Protocol
from winrm.exceptions import WinRMError, WinRMOperationTimeoutError, WinRMTransportError
import smbclient
from pathlib import Path
import os
import time
import errno

class windows():

    def __init__(self, host, username="administrator", password=""):
        self.host = host
        self.username = username
        self.password = password
        self.error = ""
        self.client = self.connect(host,username,password)

    def __del__(self):
        pass
        #self.disconnect()
        
    def connect(self,host,username,password):
        client = Protocol(endpoint="http://{0}:5985/wsman".format(host),transport="ntlm",username=username,password=password,read_timeout_sec=30)
        return client

    def disconnect(self):
        if self.client:
            self.client = None
            smbclient.delete_session(self.host)

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

    def executeCommand(self,command,args=[],elevate=False,runAs=None):
        try:
            if runAs:
                if runAs == "user":
                    smbclient.register_session(self.host, username=self.username, password=self.password, connection_timeout=30)
                    if args:
                        command = "{0}\n[murrayju.ProcessExtensions.ProcessExtensions]::StartProcessAsCurrentUser('{1}','{2}')\n".format(powershellRunAsLoggedInUser,command," ".join(args))
                    else:
                        command = "{0}\n[murrayju.ProcessExtensions.ProcessExtensions]::StartProcessAsCurrentUser('{1}')\nrm c:\\windows\\temp\\jimiRunAsUser.ps1".format(powershellRunAsLoggedInUser,command)
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

    def command(self, command, args=[], elevate=False, runAs=None):
        if self.client:
            return self.executeCommand(command,args,elevate,runAs)

    def upload(self,localFile,remotePath):
        smbclient.register_session(self.host, username=self.username, password=self.password, connection_timeout=30)
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
                smbclient.delete_session(self.host)
                return False
            smbclient.delete_session(self.host)
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
                        smbclient.delete_session(self.host)
                        return False
            smbclient.delete_session(self.host)
            return True
        return False

    def download(self,remoteFile,localPath):
        smbclient.register_session(self.host, username=self.username, password=self.password,connection_timeout=30)
        try:
            with open(localPath, mode="wb") as f:
                with smbclient.open_file("\\{0}\{1}".format(self.host,remoteFile), mode="rb") as remoteFile:
                    while True:
                        part = remoteFile.read(4096)
                        if not part:
                            break
                        f.write(part)
            smbclient.delete_session(self.host)
            return True
        except Exception as e:
            self.error = str(e)
            smbclient.delete_session(self.host)
        return False

powershellRunAsLoggedInUser = """
$Source = @"
using System;
using System.Runtime.InteropServices;

namespace murrayju.ProcessExtensions
{
    public static class ProcessExtensions
    {
        #region Win32 Constants

        private const int CREATE_UNICODE_ENVIRONMENT = 0x00000400;
        private const int CREATE_NO_WINDOW = 0x08000000;

        private const int CREATE_NEW_CONSOLE = 0x00000010;

        private const uint INVALID_SESSION_ID = 0xFFFFFFFF;
        private static readonly IntPtr WTS_CURRENT_SERVER_HANDLE = IntPtr.Zero;

        #endregion

        #region DllImports

        [DllImport("advapi32.dll", EntryPoint = "CreateProcessAsUser", SetLastError = true, CharSet = CharSet.Ansi, CallingConvention = CallingConvention.StdCall)]
        private static extern bool CreateProcessAsUser(
            IntPtr hToken,
            String lpApplicationName,
            String lpCommandLine,
            IntPtr lpProcessAttributes,
            IntPtr lpThreadAttributes,
            bool bInheritHandle,
            uint dwCreationFlags,
            IntPtr lpEnvironment,
            String lpCurrentDirectory,
            ref STARTUPINFO lpStartupInfo,
            out PROCESS_INFORMATION lpProcessInformation);

        [DllImport("advapi32.dll", EntryPoint = "DuplicateTokenEx")]
        private static extern bool DuplicateTokenEx(
            IntPtr ExistingTokenHandle,
            uint dwDesiredAccess,
            IntPtr lpThreadAttributes,
            int TokenType,
            int ImpersonationLevel,
            ref IntPtr DuplicateTokenHandle);

        [DllImport("userenv.dll", SetLastError = true)]
        private static extern bool CreateEnvironmentBlock(ref IntPtr lpEnvironment, IntPtr hToken, bool bInherit);

        [DllImport("userenv.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool DestroyEnvironmentBlock(IntPtr lpEnvironment);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr hSnapshot);

        [DllImport("kernel32.dll")]
        private static extern uint WTSGetActiveConsoleSessionId();

        [DllImport("Wtsapi32.dll")]
        private static extern uint WTSQueryUserToken(uint SessionId, ref IntPtr phToken);

        [DllImport("wtsapi32.dll", SetLastError = true)]
        private static extern int WTSEnumerateSessions(
            IntPtr hServer,
            int Reserved,
            int Version,
            ref IntPtr ppSessionInfo,
            ref int pCount);

        #endregion

        #region Win32 Structs

        private enum SW
        {
            SW_HIDE = 0,
            SW_SHOWNORMAL = 1,
            SW_NORMAL = 1,
            SW_SHOWMINIMIZED = 2,
            SW_SHOWMAXIMIZED = 3,
            SW_MAXIMIZE = 3,
            SW_SHOWNOACTIVATE = 4,
            SW_SHOW = 5,
            SW_MINIMIZE = 6,
            SW_SHOWMINNOACTIVE = 7,
            SW_SHOWNA = 8,
            SW_RESTORE = 9,
            SW_SHOWDEFAULT = 10,
            SW_MAX = 10
        }

        private enum WTS_CONNECTSTATE_CLASS
        {
            WTSActive,
            WTSConnected,
            WTSConnectQuery,
            WTSShadow,
            WTSDisconnected,
            WTSIdle,
            WTSListen,
            WTSReset,
            WTSDown,
            WTSInit
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct PROCESS_INFORMATION
        {
            public IntPtr hProcess;
            public IntPtr hThread;
            public uint dwProcessId;
            public uint dwThreadId;
        }

        private enum SECURITY_IMPERSONATION_LEVEL
        {
            SecurityAnonymous = 0,
            SecurityIdentification = 1,
            SecurityImpersonation = 2,
            SecurityDelegation = 3,
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct STARTUPINFO
        {
            public int cb;
            public String lpReserved;
            public String lpDesktop;
            public String lpTitle;
            public uint dwX;
            public uint dwY;
            public uint dwXSize;
            public uint dwYSize;
            public uint dwXCountChars;
            public uint dwYCountChars;
            public uint dwFillAttribute;
            public uint dwFlags;
            public short wShowWindow;
            public short cbReserved2;
            public IntPtr lpReserved2;
            public IntPtr hStdInput;
            public IntPtr hStdOutput;
            public IntPtr hStdError;
        }

        private enum TOKEN_TYPE
        {
            TokenPrimary = 1,
            TokenImpersonation = 2
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct WTS_SESSION_INFO
        {
            public readonly UInt32 SessionID;

            [MarshalAs(UnmanagedType.LPStr)]
            public readonly String pWinStationName;

            public readonly WTS_CONNECTSTATE_CLASS State;
        }

        #endregion

        // Gets the user token from the currently active session
        private static bool GetSessionUserToken(ref IntPtr phUserToken)
        {
            var bResult = false;
            var hImpersonationToken = IntPtr.Zero;
            var activeSessionId = INVALID_SESSION_ID;
            var pSessionInfo = IntPtr.Zero;
            var sessionCount = 0;

            // Get a handle to the user access token for the current active session.
            if (WTSEnumerateSessions(WTS_CURRENT_SERVER_HANDLE, 0, 1, ref pSessionInfo, ref sessionCount) != 0)
            {
                var arrayElementSize = Marshal.SizeOf(typeof(WTS_SESSION_INFO));
                var current = pSessionInfo;

                for (var i = 0; i < sessionCount; i++)
                {
                    var si = (WTS_SESSION_INFO)Marshal.PtrToStructure((IntPtr)current, typeof(WTS_SESSION_INFO));
                    current += arrayElementSize;

                    if (si.State == WTS_CONNECTSTATE_CLASS.WTSActive)
                    {
                        activeSessionId = si.SessionID;
                    }
                }
            }

            // If enumerating did not work, fall back to the old method
            if (activeSessionId == INVALID_SESSION_ID)
            {
                activeSessionId = WTSGetActiveConsoleSessionId();
            }

            if (WTSQueryUserToken(activeSessionId, ref hImpersonationToken) != 0)
            {
                // Convert the impersonation token to a primary token
                bResult = DuplicateTokenEx(hImpersonationToken, 0, IntPtr.Zero,
                    (int)SECURITY_IMPERSONATION_LEVEL.SecurityImpersonation, (int)TOKEN_TYPE.TokenPrimary,
                    ref phUserToken);

                CloseHandle(hImpersonationToken);
            }

            return bResult;
        }

        public static bool StartProcessAsCurrentUser(string appPath, string cmdLine = null, string workDir = null, bool visible = true)
        {
            var hUserToken = IntPtr.Zero;
            var startInfo = new STARTUPINFO();
            var procInfo = new PROCESS_INFORMATION();
            var pEnv = IntPtr.Zero;
            int iResultOfCreateProcessAsUser;

            startInfo.cb = Marshal.SizeOf(typeof(STARTUPINFO));

            try
            {
                if (!GetSessionUserToken(ref hUserToken))
                {
                    throw new Exception("StartProcessAsCurrentUser: GetSessionUserToken failed.");
                }

                uint dwCreationFlags = CREATE_UNICODE_ENVIRONMENT | (uint)(visible ? CREATE_NEW_CONSOLE : CREATE_NO_WINDOW);
                startInfo.wShowWindow = (short)(visible ? SW.SW_SHOW : SW.SW_HIDE);
                startInfo.lpDesktop = "winsta0\\\\default";

                if (!CreateEnvironmentBlock(ref pEnv, hUserToken, false))
                {
                    throw new Exception("StartProcessAsCurrentUser: CreateEnvironmentBlock failed.");
                }

                if (!CreateProcessAsUser(hUserToken,
                    appPath, // Application Name
                    cmdLine, // Command Line
                    IntPtr.Zero,
                    IntPtr.Zero,
                    false,
                    dwCreationFlags,
                    pEnv,
                    workDir, // Working directory
                    ref startInfo,
                    out procInfo))
                {
                    throw new Exception("StartProcessAsCurrentUser: CreateProcessAsUser failed.");
                }

                iResultOfCreateProcessAsUser = Marshal.GetLastWin32Error();
            }
            finally
            {
                CloseHandle(hUserToken);
                if (pEnv != IntPtr.Zero)
                {
                    DestroyEnvironmentBlock(pEnv);
                }
                CloseHandle(procInfo.hThread);
                CloseHandle(procInfo.hProcess);
            }
            return true;
        }
    }
}
"@

Add-Type -ReferencedAssemblies 'System', 'System.Runtime.InteropServices' -TypeDefinition $Source -Language CSharp
"""

