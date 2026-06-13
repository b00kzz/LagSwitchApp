Set shell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

shell.Popup "This compatibility launcher opens the visible Network Control launcher so network changes and Administrator prompts are explicit.", 8, "Network Control WebApp", 64
shell.Run """" & scriptDir & "\Start Network Control.bat" & """", 1, False
