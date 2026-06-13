Set shell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

shell.Popup "This compatibility launcher opens the visible LaxyControl launcher so network changes and Administrator prompts are explicit.", 8, "LaxyControl", 64
shell.Run """" & scriptDir & "\Start LaxyControl.bat" & """", 1, False
