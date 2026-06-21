#Requires AutoHotkey v2.0

startNum := 1
endNum := 100

baseDir := A_ScriptDir

Loop endNum - startNum + 1
{
    currentNum := startNum + A_Index - 1

    folderName := "Pack " currentNum

    if !DirExist(baseDir "\" folderName)
        continue

    archivePath := baseDir "\" folderName ".rar"

    RunWait Format(
        '"C:\Program Files\WinRAR\WinRAR.exe" a -r -m5 "{1}" "{2}"',
        archivePath,
        folderName
    ),
    baseDir,
    "Hide"
}

MsgBox "Finished packing folders."