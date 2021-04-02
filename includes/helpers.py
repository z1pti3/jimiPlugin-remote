import inspect
import textwrap
import ast

# BETA function to support SSH python remote functions ( this is because we do not want to extent jimi fully onto remote systems and this gives devs a helper function for running locally and remotely auto handled)
# This needs addition work and possible rework using pools??????? - Good starting port for additional flex
def runRemoteFunction(runRemote,persistentData,functionCall,functionInputDict,elevate=True):
    if runRemote:
        if "remote" in persistentData:
            if "client" in persistentData["remote"]:
                functionStr = inspect.getsource(functionCall)
                # Attempts to remove any indents up to 10
                for x in range(0,10):
                    if functionStr[:3] == "def":
                        break
                    functionStr = textwrap.dedent(functionStr)
                functionStr = functionStr + "\nprint({0}({1}))".format(functionCall.__name__,functionInputDict)
                client = persistentData["remote"]["client"]
                cmd = "python3 -c \"import sys;exec(sys.argv[1].replace('\\\\\\n','\\\\n'))\" \"{0}\"".format(functionStr.replace("\n","\\\\n").replace("\"","\\\""))
                if elevate:
                    exitCode, stdout, stderr = client.command(cmd,elevate=elevate)
                else:
                    exitCode, stdout, stderr = client.command(cmd,elevate=elevate)
                stdout = "".join(stdout)
                stderr = "".join(stderr)
                if exitCode == 0:
                    return ast.literal_eval(stdout)
                return { "error" : "Remote function failed", "stdout" : stdout, "stderr" : stderr, "exitCode" : exitCode }
    return functionCall(functionInputDict)
