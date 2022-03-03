from paramiko import SSHClient, AutoAddPolicy, ssh_exception
import time
import jimi
import re
import logging

from plugins.remote.includes import remote

class aruba(remote.remote):

    def __init__(self, host, deviceHostname, username="Admin", password='', enablePassword="", port=22, timeout=5):
        self.host = host
        self.deviceHostname = deviceHostname
        self.enablePassword = enablePassword
        self.username = username
        self.error = "" 
        self.type = "aruba"
        self.client = self.connect(username,password,port,timeout)

    def strip_ansi_escape_codes(self, string_buffer: str) -> str:

        code_position_cursor = chr(27) + r"\[\d+;\d+H"
        code_show_cursor = chr(27) + r"\[\?25h"
        code_next_line = chr(27) + r"E"
        code_erase_line_end = chr(27) + r"\[K"
        code_erase_line = chr(27) + r"\[2K"
        code_erase_start_line = chr(27) + r"\[K"
        code_enable_scroll = chr(27) + r"\[\d+;\d+r"
        code_insert_line = chr(27) + r"\[(\d+)L"
        code_carriage_return = chr(27) + r"\[1M"
        code_disable_line_wrapping = chr(27) + r"\[\?7l"
        code_reset_mode_screen_options = chr(27) + r"\[\?\d+l"
        code_reset_graphics_mode = chr(27) + r"\[00m"
        code_erase_display = chr(27) + r"\[2J"
        code_erase_display_0 = chr(27) + r"\[J"
        code_graphics_mode = chr(27) + r"\[\dm"
        code_graphics_mode1 = chr(27) + r"\[\d\d;\d\dm"
        code_graphics_mode2 = chr(27) + r"\[\d\d;\d\d;\d\dm"
        code_graphics_mode3 = chr(27) + r"\[(3|4)\dm"
        code_graphics_mode4 = chr(27) + r"\[(9|10)[0-7]m"
        code_get_cursor_position = chr(27) + r"\[6n"
        code_cursor_position = chr(27) + r"\[m"
        code_attrs_off = chr(27) + r"\[0m"
        code_reverse = chr(27) + r"\[7m"
        code_cursor_left = chr(27) + r"\[\d+D"
        code_cursor_forward = chr(27) + r"\[\d*C"
        code_cursor_up = chr(27) + r"\[\d*A"
        code_cursor_down = chr(27) + r"\[\d*B"
        code_wrap_around = chr(27) + r"\[\?7h"
        code_bracketed_paste_mode = chr(27) + r"\[\?2004h"

        code_set = [
            code_position_cursor,
            code_show_cursor,
            code_erase_line,
            code_enable_scroll,
            code_erase_start_line,
            code_carriage_return,
            code_disable_line_wrapping,
            code_erase_line_end,
            code_reset_mode_screen_options,
            code_reset_graphics_mode,
            code_erase_display,
            code_graphics_mode,
            code_graphics_mode1,
            code_graphics_mode2,
            code_graphics_mode3,
            code_graphics_mode4,
            code_get_cursor_position,
            code_cursor_position,
            code_erase_display,
            code_erase_display_0,
            code_attrs_off,
            code_reverse,
            code_cursor_left,
            code_cursor_up,
            code_cursor_down,
            code_cursor_forward,
            code_wrap_around,
            code_bracketed_paste_mode,
        ]

        output = string_buffer
        for ansi_esc_code in code_set:
            output = re.sub(ansi_esc_code, "", output)

        # CODE_NEXT_LINE must substitute with return
        output = re.sub(code_next_line, "\n", output)

        # Aruba and ProCurve switches can use code_insert_line for <enter>
        insert_line_match = re.search(code_insert_line, output)
        if insert_line_match:
            # Substitute each insert_line with a new <enter>
            count = int(insert_line_match.group(1))
            output = re.sub(code_insert_line, count * "\n", output)

        return output


    def connect(self,username,password,port,timeout):
        try: 
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())   
            try:
                client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=timeout,banner_timeout=timeout)
            except ssh_exception.SSHException:
                time.sleep(timeout)
                client.connect(self.host, username=username, password=password, port=port, look_for_keys=True, timeout=timeout,banner_timeout=timeout)
            self.channel = client.invoke_shell()
            if not self.recv(timeout):
                self.error = "Device detected name does not match the device name provided."
                client.close()
                return None
            return client
        except Exception as e:
           self.error = e
           return None
    
    def enable(self,username,password):
        self.channel.send("enable\n")
        if self.awaitStringRecv("Please Enter Login Name:"):
            self.channel.send("{0}\n".format(username))
            if self.awaitStringRecv("Please Enter Password:"):
                self.channel.send("{0}\n".format(password))
                if self.recv():
                    return True
        return False
    
    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None

    def awaitStringRecv(self,awaitString,timeout=5):
        startTime = time.time()
        deviceHostname = self.deviceHostname
        if len(deviceHostname) >= 20:
            deviceHostname = deviceHostname[:20]
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < timeout ):
            if self.channel.recv_ready():
                recvBuffer += self.strip_ansi_escape_codes(self.channel.recv(1024).decode().strip())
                logging.debug("danny-{0}".format(awaitString.split('\n')[-1]))
                if recvBuffer.split('\n')[-1].strip().startswith("-- MORE --, next page: Space, next line: Enter, quit: C"):
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-63]
                elif recvBuffer.split('\n')[-1].strip().endswith("Press any key to continue"):
                    logging.debug("dannyhere")
                    self.channel.send(" ")
                    recvBuffer = recvBuffer.replace("Press any key to continue","")
                elif recvBuffer.split('\n')[-1].lower().startswith(awaitString.lower()):
                    result = True
                    break
            time.sleep(0.1)
        if result:
            return recvBuffer
        return False

    def recv(self,timeout=5):
        startTime = time.time()
        deviceHostname = self.deviceHostname
        if len(deviceHostname) >= 20:
            deviceHostname = deviceHostname[:20]
        recvBuffer = ""
        result = False
        while ( time.time() - startTime < timeout ):
            if self.channel.recv_ready():
                recvBuffer += self.strip_ansi_escape_codes(self.channel.recv(1024).decode().strip())
                logging.debug("danny-{0}".format(recvBuffer.split('\n')[-1]))
                if recvBuffer.split('\n')[-1].strip().startswith("-- MORE --, next page: Space, next line: Enter, quit: C"):
                    self.channel.send(" ")
                    recvBuffer = recvBuffer[:-63]
                elif recvBuffer.split('\n')[-1].strip().endswith("Press any key to continue"):
                    logging.debug("dannyhere")
                    self.channel.send(" ")
                    recvBuffer = recvBuffer.replace("Press any key to continue","")
                elif recvBuffer.split('\n')[-1].lower().startswith(deviceHostname.lower()):
                    result = True
                    break
            time.sleep(0.1)
        if result:
            return recvBuffer
        return False

    def sendCommand(self,command):
        self.channel.send("{0}{1}".format(command,"\n"))
        return True
        
    def command(self, command, args=[], elevate=False, runAs=None, timeout=5):
        if command == "enable":
            enableResult = self.enable(self.username, self.enablePassword)
            if enableResult:
                return (0, enableResult, "")
            else:
                return (None, enableResult, "")
        elif command == "copy running-config startup-config":
            returnedData = ""
            self.sendCommand(command)
            if self.awaitStringRecv("Destination filename [startup-config]?"):
                self.sendCommand("")
                returnedData = self.recv(timeout)
                return (0, returnedData, "")
            else:
                return (None, "", "Unable to save config")
        if args:
            command = command + " " + " ".join(args)
        if self.sendCommand(command):
            returnedData = self.recv(timeout)
            if returnedData:
                returnedData = jimi.helpers.replaceBackspaces(returnedData)
            else:
                 returnedData = "Failed to retrieve data"
            maxLen = 40
            if len(command) < maxLen:
                maxLen = len(command)-1
            if command[:maxLen] not in returnedData:
                return (None,returnedData,"Unable to send command")
        else:
            return (None,"","Unable to send command")
        if returnedData == False or "% Invalid input detected at '^'" in returnedData or "% Incomplete command." in returnedData or "Command rejected" in returnedData:
            return (None,"",returnedData)
        return (0, returnedData, "")

    def __del__(self):
        self.disconnect()
