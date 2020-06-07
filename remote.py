from core import plugin, model

class _remote(plugin._plugin):
    version = 0.4

    def install(self):
        # Register models
        model.registerModel("remoteConnectLinux","_remoteConnectLinux","_action","plugins.remote.models.action")
        model.registerModel("remoteCommand","_remoteCommand","_action","plugins.remote.models.action")
        model.registerModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")
        model.registerModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        model.registerModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        return True

    def uninstall(self):
        # deregister models
        model.deregisterModel("remoteConnectLinux","_remoteConnectLinux","_action","plugins.remote.models.action")
        model.deregisterModel("remoteCommand","_remoteCommand","_action","plugins.remote.models.action")
        model.deregisterModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")
        model.deregisterModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        model.deregisterModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        return True

    def upgrade(self,LatestPluginVersion):
        if self.version < 0.4:
            model.registerModel("remoteUpload","_remoteUpload","_action","plugins.remote.models.action")
        if self.version < 0.3:
            model.registerModel("remoteDownload","_remoteDownload","_action","plugins.remote.models.action")
        if self.version < 0.2:
            model.registerModel("remoteConnectWindows","_remoteConnectWindows","_action","plugins.remote.models.action")