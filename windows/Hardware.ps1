# Local read-only CIM queries. No network, Fastfetch, elevation or guessed sensors.
function Get-PokemonWindowsHardware {
    $errors = New-Object 'System.Collections.Generic.List[string]'
    function Read-Cim($Class) {
        try { Get-CimInstance -ClassName $Class -ErrorAction Stop }
        catch { $errors.Add($Class + ': ' + $_.Exception.Message) }
    }
    $cpu = @(Read-Cim Win32_Processor)
    $gpus = @(Read-Cim Win32_VideoController)
    $os = Read-Cim Win32_OperatingSystem
    $computer = Read-Cim Win32_ComputerSystem
    $disks = @(Read-Cim Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 -and $_.Size -gt 0 })
    $data = @{
        gpu = @($gpus | ForEach-Object { @{ name = $_.Name } })
        disk = @($disks | ForEach-Object { @{
            mountpoint = $_.DeviceID; mountFrom = $_.DeviceID
            bytes = @{ total = [double]$_.Size; used = [double]$_.Size - [double]$_.FreeSpace }
        } })
        host = @{ name = $computer.Model; version = $computer.Manufacturer }
        os = @{ prettyName = $os.Caption }
        kernel = @{ name = 'Windows NT'; release = $os.Version; architecture = $os.OSArchitecture }
        shell = @{ name = 'Windows PowerShell'; version = $PSVersionTable.PSVersion.ToString() }
        terminal = @{ name = 'Windows Terminal' }
        de = @{ name = 'Windows Desktop' }; wm = @{ name = 'Desktop Window Manager' }
        packages = @{ all = 'Not collected' }
    }
    if ($cpu.Count -gt 0) {
        $data.cpu = @{ cpu = ($cpu.Name -join ' / ')
            cores = @{ online = ($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum }
            frequency = @{ max = ($cpu | Measure-Object MaxClockSpeed -Maximum).Maximum } }
    }
    if ($os) {
        $data.memory = @{ total = [double]$os.TotalVisibleMemorySize * 1024
            used = ([double]$os.TotalVisibleMemorySize - [double]$os.FreePhysicalMemory) * 1024 }
        $data.uptime = @{ uptime = [math]::Max(0, ((Get-Date) - $os.LastBootUpTime).TotalMilliseconds) }
    }
    $data.probeErrors = @($errors.ToArray())
    return $data
}
