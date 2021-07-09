class remote():

    def command(self, command, args=[], elevate=False, runAs=None, timeout=None):
        self.error = "Not implimented"
        return (-2555, "Not implimented", "Not implimented")

    def reboot(self,timeout):
        # Not implimented yet!
        self.error = "Not implimented"
        return False

    def upload(self, localFile, remotePath):
        # Not supported!
        self.error = "Not supported"
        return False

    def download(self, remoteFile, localPath, createMissingFolders):
        # Not supported!
        self.error = "Not supported"
        return False
