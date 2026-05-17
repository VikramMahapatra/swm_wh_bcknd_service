param(
    [string]$AdminApiUrl = "http://127.0.0.1:8003",
    [string]$WebSocketUrl = "ws://127.0.0.1:8002/ws/realtime",
    [string]$OutputPath = ".\realtime-watch.log",
    [int]$DurationMinutes = 0
)

$ErrorActionPreference = "Stop"

function Write-LogLine {
    param(
        [Parameter(Mandatory = $true)][string]$Message
    )

    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $OutputPath -Value $line
}

function Convert-BytesToUtf8String {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Bytes,
        [Parameter(Mandatory = $true)][int]$Count
    )

    return [System.Text.Encoding]::UTF8.GetString($Bytes, 0, $Count)
}

function Get-LivePayloadRecords {
    param(
        [Parameter(Mandatory = $true)]$Payload
    )

    if ($null -eq $Payload) {
        return @()
    }

    if ($Payload -is [string]) {
        $trimmed = $Payload.Trim()
        if (-not $trimmed) {
            return @()
        }

        try {
            return @(($trimmed | ConvertFrom-Json))
        }
        catch {
            return @($Payload)
        }
    }

    if ($null -ne $Payload.payload) {
        return @(Get-LivePayloadRecords -Payload $Payload.payload)
    }

    if ($null -ne $Payload.data) {
        return @(Get-LivePayloadRecords -Payload $Payload.data)
    }

    if ($Payload -is [System.Collections.IEnumerable] -and -not ($Payload -is [string])) {
        return @($Payload)
    }

    return @($Payload)
}

function Get-RecordValue {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    foreach ($name in $Names) {
        if ($null -ne $Record.$name -and "$($Record.$name)".Trim()) {
            return $Record.$name
        }
    }

    return ""
}

function Format-LiveRecord {
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string]$Prefix
    )

    $imei = Get-RecordValue -Record $Record -Names @("imei", "IMEI")
    $vehicle = Get-RecordValue -Record $Record -Names @("vehicle_id", "vehicleId", "vehicle")
    $lat = Get-RecordValue -Record $Record -Names @("lat", "latitude")
    $lng = Get-RecordValue -Record $Record -Names @("lng", "lon", "longitude")
    $speed = Get-RecordValue -Record $Record -Names @("speed", "speed_kph", "speedKph")
    $status = Get-RecordValue -Record $Record -Names @("status", "state")
    $ts = Get-RecordValue -Record $Record -Names @("event_ts", "ts", "timestamp", "time")

    return "{0} imei={1} vehicle={2} lat={3} lng={4} speed={5} status={6} ts={7}" -f @(
        $Prefix,
        $imei,
        $vehicle,
        $lat,
        $lng,
        $speed,
        $status,
        $ts
    )
}

function Get-InitialSnapshot {
    $url = "$($AdminApiUrl.TrimEnd('/'))/v1/realtime/trucks"
    Write-LogLine "Fetching snapshot from $url"

    $response = Invoke-RestMethod -Method Get -Uri $url -Headers @{ "x-role" = "viewer" }
    $items = @($response.items)

    Write-LogLine ("Snapshot total={0} items={1}" -f ($response.total), $items.Count)

    foreach ($item in $items) {
        $summary = "SNAPSHOT imei={0} vehicle={1} lat={2} lng={3} speed={4} status={5} ts={6}" -f @(
            $item.imei,
            $(if ($null -ne $item.vehicle_id) { $item.vehicle_id } else { "" }),
            $item.lat,
            $item.lng,
            $item.speed_kph,
            $item.status,
            $item.event_ts
        )
        Write-LogLine $summary
    }
}

function Receive-WebSocketUpdates {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$Minutes = 0
    )

    $client = [System.Net.WebSockets.ClientWebSocket]::new()
    $uri = [Uri]$Url
    $buffer = New-Object byte[] 8192
    $messageBuffer = New-Object System.Collections.Generic.List[byte]
    $deadline = if ($Minutes -gt 0) { (Get-Date).AddMinutes($Minutes) } else { $null }

    Write-LogLine "Connecting websocket to $Url"
    $client.ConnectAsync($uri, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()
    Write-LogLine "WebSocket connected"

    try {
        while ($client.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            if ($deadline -and (Get-Date) -ge $deadline) {
                Write-LogLine "Duration reached; closing websocket"
                break
            }

            $result = $client.ReceiveAsync([ArraySegment[byte]]::new($buffer), [System.Threading.CancellationToken]::None).GetAwaiter().GetResult()

            if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                Write-LogLine "WebSocket close frame received"
                break
            }

            if ($result.Count -gt 0) {
                for ($i = 0; $i -lt $result.Count; $i++) {
                    [void]$messageBuffer.Add($buffer[$i])
                }
            }

            if (-not $result.EndOfMessage) {
                continue
            }

            $rawMessage = Convert-BytesToUtf8String -Bytes $messageBuffer.ToArray() -Count $messageBuffer.Count
            $messageBuffer.Clear()

            try {
                $payload = $rawMessage | ConvertFrom-Json

                $records = Get-LivePayloadRecords -Payload $payload
                if ($records.Count -eq 0) {
                    Write-LogLine "WS raw=$rawMessage"
                    continue
                }

                foreach ($record in $records) {
                    if ($record -is [string]) {
                        Write-LogLine "WS raw=$record"
                        continue
                    }

                    Write-LogLine (Format-LiveRecord -Record $record -Prefix "WS")
                }
            }
            catch {
                Write-LogLine "WS raw=$rawMessage"
            }
        }
    }
    finally {
        if ($client.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            $client.Abort()
            $client.Dispose()
        }
    }
}

if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}

Write-LogLine "Starting realtime watcher"
Get-InitialSnapshot
Receive-WebSocketUpdates -Url $WebSocketUrl -Minutes $DurationMinutes
Write-LogLine "Watcher finished"
