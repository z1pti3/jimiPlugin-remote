from core import plugin, model

class _remote(plugin._plugin):
    version = 1.3

    def install(self):
        # Register models
        model.registerModel("remoteConnectLinux","_remoteConnectLinux","_action","plugins.remote.models.action")
        model.registerModel("remoteCommand","_remoteCommand","_action","plugins.remote.models.action")
        model.registerModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")
        model.registerModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        model.registerModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        model.registerModel("remoteDisconnect","_remoteDisconnect","_action","plugins.remote.models.action")
        model.registerModel("remoteReboot","_remoteReboot","_action","plugins.remote.models.action")
        model.registerModel("linuxStartPortForward","_remoteLinuxStartPortForward","_action","plugins.remote.models.action")        
        model.registerModel("linuxStopPortForward","_remoteLinuxStopPortForward","_action","plugins.remote.models.action")   
        model.registerModel("remotePullWinEvents","_remotePullWinEvents","_trigger","plugins.remote.models.trigger")      
        model.registerModel("remoteConnectFortigate","_remoteConnectFortigate","_action","plugins.remote.models.action")
        model.registerModel("remoteMultiCommand","_remoteMultiCommand","_action","plugins.remote.models.action")
        return True
        

    def uninstall(self):
        # deregister models
        model.deregisterModel("remoteConnectLinux","_remoteConnectLinux","_action","plugins.remote.models.action")
        model.deregisterModel("remoteCommand","_remoteCommand","_action","plugins.remote.models.action")
        model.deregisterModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")
        model.deregisterModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        model.deregisterModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        model.deregisterModel("remoteDisconnect","_remoteDisconnect","_action","plugins.remote.models.action")
        model.deregisterModel("remoteReboot","_remoteReboot","_action","plugins.remote.models.action")
        model.deregisterModel("remotePullWinEvents","_remotePullWinEvents","_trigger","plugins.remote.models.trigger") 
        model.deregisterModel("remoteConnectFortigate","_remoteConnectFortigate","_action","plugins.remote.models.action")  
        model.deregisterModel("remoteMultiCommand","_remoteMultiCommand","_action","plugins.remote.models.action") 
        return True

    def upgrade(self,LatestPluginVersion):
        if self.version < 1.1:
            model.registerModel("remotePullWinEvents","_remotePullWinEvents","_trigger","plugins.remote.models.trigger")   
        if self.version < 0.7:
            model.registerModel("remoteReboot","_remoteReboot","_action","plugins.remote.models.action")
        if self.version < 0.5:
            model.registerModel("remoteDisconnect","_remoteDisconnect","_action","plugins.remote.models.action")
        if self.version < 0.4:
            model.registerModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        if self.version < 0.3:
            model.registerModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        if self.version < 0.2:
            model.registerModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")
        if self.version < 1.2:
            model.registerModel("remoteConnectFortigate","_remoteConnectFortigate","_action","plugins.remote.models.action")
        if self.version < 1.3:
            model.registerModel("remoteMultiCommand","_remoteMultiCommand","_action","plugins.remote.models.action")

        return True



