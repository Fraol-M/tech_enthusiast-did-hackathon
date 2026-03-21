param(
    [string]$VerifyApiUrl = "http://localhost:18080/v1/verify",
    [string]$VerifyUiUrl = "http://localhost:13000",
    [string]$ConfigPath = ".\\config\\config.json",
    [string]$ClaimName = "MOSIP ID",
    [string]$ClientId = "did:web:localhost:13000:v1:verify",
    [string]$TransactionId = "",
    [string]$Nonce = ""
)

$ErrorActionPreference = "Stop"

if (-not [System.IO.Path]::IsPathRooted($ConfigPath)) {
    $ConfigPath = Join-Path -Path $PSScriptRoot -ChildPath $ConfigPath
}

if (-not (Test-Path $ConfigPath)) {
    throw "Could not find config file at '$ConfigPath'."
}

if ([string]::IsNullOrWhiteSpace($TransactionId)) {
    $TransactionId = "demo-txn-{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 8))
}

if ([string]::IsNullOrWhiteSpace($Nonce)) {
    $Nonce = "demo-nonce-{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 8))
}

$health = Invoke-RestMethod -Method GET -Uri "$VerifyApiUrl/actuator/health"
if ($health.status -ne "UP") {
    throw "Inji Verify is not reachable at $VerifyApiUrl."
}

$config = Get-Content -Raw $ConfigPath | ConvertFrom-Json
$claim = $config.verifiableClaims | Where-Object { $_.name -eq $ClaimName } | Select-Object -First 1

if (-not $claim) {
    $available = ($config.verifiableClaims | ForEach-Object { $_.name }) -join ", "
    throw "Claim '$ClaimName' was not found. Available claims: $available"
}

$definitionId = ($claim.type -replace '[^A-Za-z0-9]+', '-').ToLowerInvariant()

$presentationDefinition = [ordered]@{
    id = $definitionId
    name = $claim.name
    purpose = $claim.definition.purpose
    format = $claim.definition.format
    input_descriptors = $claim.definition.input_descriptors
}

$body = @{
    clientId = $ClientId
    transactionId = $TransactionId
    nonce = $Nonce
    presentationDefinition = $presentationDefinition
    acceptVPWithoutHolderProof = $true
}

$response = Invoke-RestMethod `
    -Method POST `
    -Uri "$VerifyApiUrl/vp-request" `
    -ContentType "application/json" `
    -Body ($body | ConvertTo-Json -Depth 25)

$status = Invoke-RestMethod -Method GET -Uri "$VerifyApiUrl/vp-request/$($response.requestId)/status"

$summary = [ordered]@{
    verifyUiUrl = $VerifyUiUrl
    verifyApiUrl = $VerifyApiUrl
    claimName = $claim.name
    claimType = $claim.type
    clientId = $ClientId
    transactionId = $response.transactionId
    requestId = $response.requestId
    initialStatus = $status.status
    expiresAt = $response.expiresAt
    requestUri = $response.requestUri
    backendRequestUrl = "$VerifyApiUrl/vp-request/$($response.requestId)"
    statusUrl = "$VerifyApiUrl/vp-request/$($response.requestId)/status"
    resultUrl = "$VerifyApiUrl/vp-result/$($response.transactionId)"
}

$summaryPath = Join-Path -Path $PSScriptRoot -ChildPath "last-vp-request.json"
$requestUriPath = Join-Path -Path $PSScriptRoot -ChildPath "last-vp-request-uri.txt"

$summary | ConvertTo-Json -Depth 25 | Set-Content -Path $summaryPath
$response.requestUri | Set-Content -Path $requestUriPath

Write-Host ""
Write-Host "Created a demo VP request." -ForegroundColor Green
Write-Host "  claim: $($claim.name)"
Write-Host "  requestId: $($response.requestId)"
Write-Host "  transactionId: $($response.transactionId)"
Write-Host "  status: $($status.status)"
Write-Host ""
Write-Host "Open the verifier UI here:" -ForegroundColor Green
Write-Host "  $VerifyUiUrl"
Write-Host ""
Write-Host "The generated request URI is:" -ForegroundColor Green
Write-Host "  $($response.requestUri)"
Write-Host ""
Write-Host "Saved files:" -ForegroundColor Green
Write-Host "  $summaryPath"
Write-Host "  $requestUriPath"
Write-Host ""
