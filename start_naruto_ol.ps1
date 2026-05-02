[CmdletBinding()]
param(
    [string]$LauncherPath = "E:\360Game5\bin\360Game.exe",
    [string]$GameName = "Naruto OL",
    [int]$LaunchWaitSeconds = 12,
    [int]$SearchResultWaitSeconds = 5,
    [int]$PostResultWaitSeconds = 4,
    [switch]$SkipSearchHotkey,
    [string]$SearchHotkey = "^f",
    [Nullable[int]]$SearchBoxX = $null,
    [Nullable[int]]$SearchBoxY = $null,
    [Nullable[int]]$FirstResultX = $null,
    [Nullable[int]]$FirstResultY = $null,
    [Nullable[int]]$PlayButtonX = $null,
    [Nullable[int]]$PlayButtonY = $null
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeMethods {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }
}
"@

$MouseLeftDown = 0x0002
$MouseLeftUp = 0x0004
$ShowNormal = 1
$ShowMaximized = 3

function Write-Step {
    param([string]$Message)
    Write-Host "[auto360] $Message"
}

function Set-MousePosition {
    param(
        [Parameter(Mandatory)]
        [int]$X,
        [Parameter(Mandatory)]
        [int]$Y
    )

    [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($X, $Y)
}

function Invoke-LeftClick {
    param(
        [Parameter(Mandatory)]
        [int]$X,
        [Parameter(Mandatory)]
        [int]$Y,
        [int]$PauseMilliseconds = 350
    )

    Set-MousePosition -X $X -Y $Y
    Start-Sleep -Milliseconds 200
    [NativeMethods]::mouse_event($MouseLeftDown, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [NativeMethods]::mouse_event($MouseLeftUp, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds $PauseMilliseconds
}

function Send-Keys {
    param(
        [Parameter(Mandatory)]
        [string]$Keys,
        [int]$PauseMilliseconds = 500
    )

    [System.Windows.Forms.SendKeys]::SendWait($Keys)
    Start-Sleep -Milliseconds $PauseMilliseconds
}

function Send-Text {
    param(
        [Parameter(Mandatory)]
        [string]$Text,
        [int]$PauseMilliseconds = 500
    )

    [Microsoft.VisualBasic.Interaction]::AppActivate($script:TargetProcess.Id) | Out-Null
    Start-Sleep -Milliseconds 300
    Set-Clipboard -Value $Text
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    Start-Sleep -Milliseconds 150
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds $PauseMilliseconds
}

function Wait-ForWindow {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $Process.Refresh()
        } catch {
            return $null
        }

        if ($Process.MainWindowHandle -ne 0) {
            return $Process
        }

        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    return $Process
}

function Focus-Window {
    param(
        [Parameter(Mandatory)]
        [System.Diagnostics.Process]$Process
    )

    $Process.Refresh()
    if ($Process.MainWindowHandle -eq 0) {
        throw "360 Game Hall window was not found. Please confirm it is visible."
    }

    [NativeMethods]::ShowWindowAsync($Process.MainWindowHandle, $ShowNormal) | Out-Null
    Start-Sleep -Milliseconds 300
    [NativeMethods]::ShowWindowAsync($Process.MainWindowHandle, $ShowMaximized) | Out-Null
    Start-Sleep -Milliseconds 300
    [NativeMethods]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500
}

function Start-Launcher {
    if (-not (Test-Path -LiteralPath $LauncherPath)) {
        throw "Launcher file was not found: $LauncherPath"
    }

    Write-Step "Starting 360 Game Hall"
    $process = Start-Process -FilePath $LauncherPath -PassThru
    Start-Sleep -Seconds $LaunchWaitSeconds
    return Wait-ForWindow -Process $process -TimeoutSeconds 20
}

function Invoke-SearchFlow {
    Write-Step "Searching game: $GameName"

    if (-not $SkipSearchHotkey) {
        try {
            Send-Keys -Keys $SearchHotkey -PauseMilliseconds 700
            Send-Text -Text $GameName -PauseMilliseconds 600
            Send-Keys -Keys "{ENTER}" -PauseMilliseconds 800
            Start-Sleep -Seconds $SearchResultWaitSeconds
            return
        } catch {
            Write-Step "Hotkey search failed. Falling back to coordinate mode."
        }
    }

    if ($null -eq $SearchBoxX -or $null -eq $SearchBoxY) {
        throw "Search box coordinates are missing and hotkey mode is unavailable."
    }

    Invoke-LeftClick -X $SearchBoxX -Y $SearchBoxY
    Send-Text -Text $GameName -PauseMilliseconds 600
    Send-Keys -Keys "{ENTER}" -PauseMilliseconds 800
    Start-Sleep -Seconds $SearchResultWaitSeconds
}

function Invoke-ResultFlow {
    if ($null -ne $FirstResultX -and $null -ne $FirstResultY) {
        Write-Step "Clicking the first search result"
        Invoke-LeftClick -X $FirstResultX -Y $FirstResultY -PauseMilliseconds 800
        Start-Sleep -Seconds $PostResultWaitSeconds
    } else {
        Write-Step "Result coordinates are missing. Trying Enter on the first result."
        Send-Keys -Keys "{ENTER}" -PauseMilliseconds 1000
        Start-Sleep -Seconds $PostResultWaitSeconds
    }

    if ($null -ne $PlayButtonX -and $null -ne $PlayButtonY) {
        Write-Step "Clicking the Play button"
        Invoke-LeftClick -X $PlayButtonX -Y $PlayButtonY -PauseMilliseconds 800
    } else {
        Write-Step "Play button coordinates are missing. Please verify whether the game opened."
    }
}

try {
    $script:TargetProcess = Start-Launcher
    Focus-Window -Process $script:TargetProcess
    Invoke-SearchFlow
    Focus-Window -Process $script:TargetProcess
    Invoke-ResultFlow
    Write-Step "Flow finished. If the game did not start, run capture_point.ps1 and retry with coordinates."
} catch {
    Write-Error $_
    exit 1
}
