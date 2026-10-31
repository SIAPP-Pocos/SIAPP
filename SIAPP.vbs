' Abre o SIAPP sem janela de console (o wscript nao abre nenhuma).
' Quem faz o trabalho e o SIAPP.pyw; aqui so se acha um Python com pythonw.
Option Explicit
Dim sh, fso, pasta, pyw, tentativas, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = """" & pasta & "\SIAPP.pyw"""
sh.CurrentDirectory = pasta
' variaveis que fazem o Python procurar a biblioteca no lugar errado
sh.Environment("Process").Remove "PYTHONHOME"
sh.Environment("Process").Remove "PYTHONPATH"

' 1) Python Launcher (sem console)  2) pythonw da .venv, se ja existir
tentativas = Array("pyw -3 " & pyw, """" & pasta & "\.venv\Scripts\pythonw.exe"" " & pyw)
On Error Resume Next
For i = 0 To UBound(tentativas)
  Err.Clear
  sh.Run tentativas(i), 0, False
  If Err.Number = 0 Then WScript.Quit 0
Next
On Error GoTo 0
MsgBox "Nao encontrei o Python neste computador." & vbCrLf & vbCrLf & _
       "Instale o Python (Microsoft Store ou python.org) e abra o SIAPP de novo.", vbCritical, "SIAPP"
