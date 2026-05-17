param(
    [string]$BaseUrl = "http://127.0.0.1:8001",
    [string]$Endpoint = "/webhook/gps",
    [int]$DurationMinutes = 10,
    [int]$Trucks = 10,
    [double]$CenterLat = 18.5516,
    [double]$CenterLng = 73.9483,
    [double]$OrbitRadiusDeg = 0.0020,
    [switch]$VerboseProgress
)

$ErrorActionPreference = "Stop"

if ($Trucks -lt 1) {
    throw "Trucks must be >= 1"
}

$url = "$($BaseUrl.TrimEnd('/'))$Endpoint"
$vendors = @("vendor_a", "vendor_b", "vendor_c")
$imeis = @()

for ($i = 0; $i -lt $Trucks; $i++) {
    $imeiNum = 990000000000000 + $i
    $imeis += ("{0:D15}" -f $imeiNum)
}

$stopAt = (Get-Date).AddMinutes($DurationMinutes)
$tick = 0
$sentRequests = 0
$ok2xx = 0
$failCount = 0
$errorSampleCount = 0
$accepted = 0
$published = 0

Write-Host "[kharadi-live] start url=$url trucks=$Trucks duration_minutes=$DurationMinutes center=($CenterLat,$CenterLng)" -ForegroundColor Cyan

while ((Get-Date) -lt $stopAt) {
    for ($i = 0; $i -lt $imeis.Count; $i++) {
        $imei = $imeis[$i]
        $vendor = $vendors[$i % $vendors.Count]

        $angleDeg = ($tick * 8 + $i * (360 / [Math]::Max($Trucks, 1))) % 360
        $angle = $angleDeg * [Math]::PI / 180.0

        $noiseLat = (Get-Random -Minimum -35 -Maximum 35) / 100000.0
        $noiseLng = (Get-Random -Minimum -35 -Maximum 35) / 100000.0

        $lat = [Math]::Round($CenterLat + ($OrbitRadiusDeg * [Math]::Cos($angle)) + $noiseLat, 6)
        $lng = [Math]::Round($CenterLng + ($OrbitRadiusDeg * [Math]::Sin($angle)) + $noiseLng, 6)
        $speed = [Math]::Round((Get-Random -Minimum 8 -Maximum 46), 2)

        $event = @{
            imei = $imei
            device_id = "device-$imei"
            vehicle_id = "vehicle-$imei"
            latitude = $lat
            longitude = $lng
            speed = $speed
            heading = [int](Get-Random -Minimum 0 -Maximum 359)
            ignition = $true
            odometer = [Math]::Round((10000 + $tick * 0.05 + $i), 3)
            fuel_level = [Math]::Round((Get-Random -Minimum 20 -Maximum 90), 2)
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        }

        # PowerShell 5.1 lacks ConvertTo-Json -AsArray, so wrap manually.
        $payload = "[" + ($event | ConvertTo-Json -Depth 4 -Compress) + "]"
        $headers = @{
            "X-Vendor-Id" = $vendor
            "X-Request-Id" = "kharadi-live-$([guid]::NewGuid().ToString())"
        }

        try {
            $resp = Invoke-WebRequest -Uri $url -Method Post -Headers $headers -ContentType "application/json; charset=utf-8" -Body $payload -UseBasicParsing
            $sentRequests++
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
                $ok2xx++
                # Parse response to extract accepted/published counts
                try {
                    $respData = $resp.Content | ConvertFrom-Json
                    $accepted += [int]($respData.accepted -or 0)
                    $published += [int]($respData.published -or 0)
                }
                catch {
                    # silently ignore parse errors
                }
            }
            else {
                $failCount++
                if ($errorSampleCount -lt 5) {
                    Write-Host "[kharadi-live] non_2xx status=$($resp.StatusCode) imei=$imei" -ForegroundColor Yellow
                    $errorSampleCount++
                }
            }
        }
        catch {
            $sentRequests++
            $failCount++
            if ($VerboseProgress -or $errorSampleCount -lt 5) {
                $statusCode = "unknown"
                $responseBody = ""
                if ($_.Exception.Response) {
                    try {
                        $statusCode = [int]$_.Exception.Response.StatusCode
                    }
                    catch {
                        $statusCode = "unknown"
                    }
                    try {
                        $stream = $_.Exception.Response.GetResponseStream()
                        if ($stream) {
                            $reader = New-Object System.IO.StreamReader($stream)
                            $responseBody = $reader.ReadToEnd()
                            $reader.Close()
                        }
                    }
                    catch {
                        $responseBody = ""
                    }
                }

                Write-Host "[kharadi-live] request_failed imei=$imei status=$statusCode error=$($_.Exception.Message) body=$responseBody" -ForegroundColor Yellow
                if ($errorSampleCount -lt 5) {
                    $errorSampleCount++
                }
            }
        }
    }

    $tick++
    if ($tick % 10 -eq 0) {
        Write-Host "[kharadi-live] second=$tick sent=$sentRequests ok2xx=$ok2xx failed=$failCount accepted=$accepted published=$published" -ForegroundColor Gray
    }

    Start-Sleep -Seconds 1
}

Write-Host "[kharadi-live] done sent=$sentRequests ok2xx=$ok2xx failed=$failCount accepted=$accepted published=$published" -ForegroundColor Green
