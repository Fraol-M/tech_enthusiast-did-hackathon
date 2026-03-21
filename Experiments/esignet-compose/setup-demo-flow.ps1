param(
    [string]$BaseUrl = "http://localhost:8088",
    [string]$UiUrl = "http://localhost:3000",
    [string]$MockIdentityUrl = "http://localhost:8082",
    [string]$ClientId = "",
    [string]$RedirectUri = "http://localhost:5555/callback",
    [string]$IndividualId = "5555444433"
)

$ErrorActionPreference = "Stop"

function ConvertTo-Base64Url {
    param([byte[]]$Bytes)

    ([Convert]::ToBase64String($Bytes)).TrimEnd("=") -replace "\+", "-" -replace "/", "_"
}

function New-RsaPublicJwk {
    $rsa = [System.Security.Cryptography.RSA]::Create(2048)
    $params = $rsa.ExportParameters($false)
    $modulusBase64Url = ConvertTo-Base64Url -Bytes $params.Modulus
    $derivedClientId = $modulusBase64Url

    if ($derivedClientId.Length -gt 50) {
        $derivedClientId = $derivedClientId.Substring(2, 48)
    }

    [pscustomobject]@{
        Jwk = [ordered]@{
            kty = "RSA"
            e = ConvertTo-Base64Url -Bytes $params.Exponent
            n = $modulusBase64Url
        }
        DerivedClientId = $derivedClientId
    }
}

function New-PkcePair {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()

    while ($true) {
        $verifierBytes = New-Object byte[] 32
        $rng.GetBytes($verifierBytes)

        $codeVerifier = ConvertTo-Base64Url -Bytes $verifierBytes
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $codeChallenge = ConvertTo-Base64Url -Bytes ($sha.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($codeVerifier)))

        if ($codeVerifier -match '^[A-Za-z0-9]+$' -and $codeChallenge -match '^[A-Za-z0-9]+$') {
            return [pscustomobject]@{
                CodeVerifier = $codeVerifier
                CodeChallenge = $codeChallenge
                CodeChallengeMethod = "S256"
            }
        }
    }
}

function Invoke-Json {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [hashtable]$Headers = @{},
        [Microsoft.PowerShell.Commands.WebRequestSession]$WebSession
    )

    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $Headers
        WebSession = $WebSession
        ContentType = "application/json"
    }

    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }

    Invoke-RestMethod @params
}

function Test-MockIdentityExists {
    param(
        [string]$MockIdentityUrl,
        [string]$IndividualId
    )

    $result = Invoke-RestMethod -Method GET -Uri "$MockIdentityUrl/v1/mock-identity-system/identity/$IndividualId"
    return ($null -ne $result.response -and -not $result.errors)
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$health = Invoke-RestMethod -Method GET -Uri "$BaseUrl/v1/esignet/actuator/health" -WebSession $session
if ($health.status -ne "UP") {
    throw "eSignet is not reachable at $BaseUrl."
}

$csrf = Invoke-RestMethod -Method GET -Uri "$BaseUrl/v1/esignet/csrf/token" -WebSession $session
if (-not $csrf.token) {
    throw "Could not fetch the eSignet CSRF token."
}

$headers = @{
    "X-XSRF-TOKEN" = $csrf.token
}

if (-not (Test-MockIdentityExists -MockIdentityUrl $MockIdentityUrl -IndividualId $IndividualId)) {
    $userBody = @{
        requestTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        request = @{
            individualId = $IndividualId
            pin = "1234"
            email = "amina.demo@example.com"
            phone = "+251911223344"
            fullName = @(@{ language = "eng"; value = "Amina Hassan" })
            nickName = @(@{ language = "eng"; value = "Amina" })
            preferredUsername = @(@{ language = "eng"; value = "Amina Hassan" })
            givenName = @(@{ language = "eng"; value = "Amina" })
            middleName = @(@{ language = "eng"; value = "K" })
            familyName = @(@{ language = "eng"; value = "Hassan" })
            gender = @(@{ language = "eng"; value = "Female" })
            dateOfBirth = "1996/04/03"
            streetAddress = @(@{ language = "eng"; value = "Kebribeyah Camp" })
            locality = @(@{ language = "eng"; value = "Jijiga" })
            password = "Passw0rd!"
            preferredLang = "eng"
            locale = "en"
            region = @(@{ language = "eng"; value = "Somali" })
            zoneInfo = "EAT"
            postalCode = "1000"
            country = @(@{ language = "eng"; value = "Ethiopia" })
            encodedPhoto = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
        }
    }

    $null = Invoke-RestMethod `
        -Method POST `
        -Uri "$MockIdentityUrl/v1/mock-identity-system/identity" `
        -ContentType "application/json" `
        -Body ($userBody | ConvertTo-Json -Depth 20 -Compress)

    if (-not (Test-MockIdentityExists -MockIdentityUrl $MockIdentityUrl -IndividualId $IndividualId)) {
        throw "Mock identity creation did not produce a usable identity for '$IndividualId'."
    }
}

$clientReady = $false
$maxAttempts = 5
$attempt = 0
$fixedClientId = -not [string]::IsNullOrWhiteSpace($ClientId)

while (-not $clientReady -and $attempt -lt $maxAttempts) {
    $attempt++

    $publicKeyInfo = New-RsaPublicJwk
    $pkce = New-PkcePair

    if (-not $fixedClientId) {
        $ClientId = $publicKeyInfo.DerivedClientId
    }

    $clientBody = @{
        requestTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        request = @{
            clientId = $ClientId
            clientName = "RefuPass Local Demo"
            publicKey = $publicKeyInfo.Jwk
            relyingPartyId = "mock-relying-party-id"
            userClaims = @("name", "email", "gender", "phone_number", "picture", "birthdate")
            authContextRefs = @(
                "mosip:idp:acr:generated-code",
                "mosip:idp:acr:password",
                "mosip:idp:acr:linked-wallet"
            )
            logoUri = "https://example.com/refupass-logo.png"
            redirectUris = @($RedirectUri)
            grantTypes = @("authorization_code")
            clientAuthMethods = @("private_key_jwt")
            additionalConfig = @{
                userinfo_response_type = "JWS"
                purpose = @{ type = "verify" }
                signup_banner_required = $true
                forgot_pwd_link_required = $true
                consent_expire_in_mins = 20
            }
        }
    }

    $clientResponse = Invoke-Json `
        -Method POST `
        -Url "$BaseUrl/v1/esignet/client-mgmt/client" `
        -Body $clientBody `
        -Headers $headers `
        -WebSession $session

    if ($clientResponse.errors) {
        if ($fixedClientId) {
            throw "Could not create or update the local OIDC client."
        }
        continue
    }

    $oauthCheckBody = @{
        requestTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        request = @{
            clientId = $ClientId
            scope = "openid profile"
            responseType = "code"
            redirectUri = $RedirectUri
            display = "popup"
            prompt = "login"
            acrValues = "mosip:idp:acr:generated-code"
            claims = @{
                userinfo = @{
                    given_name = @{ essential = $true }
                    phone_number = @{ essential = $false }
                    email = @{ essential = $true }
                    picture = @{ essential = $false }
                    gender = @{ essential = $false }
                    birthdate = @{ essential = $false }
                    address = @{ essential = $false }
                }
                id_token = @{}
            }
            nonce = "refupassnonce123"
            state = "refupassstate123"
            claimsLocales = "en"
            codeChallenge = $pkce.CodeChallenge
            codeChallengeMethod = "S256"
        }
    }

    $oauthCheck = Invoke-Json `
        -Method POST `
        -Url "$BaseUrl/v1/esignet/authorization/v3/oauth-details" `
        -Body $oauthCheckBody `
        -Headers $headers `
        -WebSession $session

    if ($oauthCheck.response.transactionId) {
        $clientReady = $true
        break
    }

    if ($fixedClientId) {
        throw "The supplied client ID was created, but eSignet still rejected it during oauth-details."
    }
}

if (-not $clientReady) {
    throw "Could not create a browser-usable eSignet client after $maxAttempts attempts."
}

$authorizeUrl = "{0}/authorize?nonce={1}&state={2}&client_id={3}&redirect_uri={4}&scope={5}&response_type=code&acr_values={6}&claims_locales=en&ui_locales=en-IN&code_challenge={7}&code_challenge_method={8}" -f `
    $UiUrl.TrimEnd("/"), `
    "refupassnonce123", `
    "refupassstate123", `
    [uri]::EscapeDataString($ClientId), `
    [uri]::EscapeDataString($RedirectUri), `
    [uri]::EscapeDataString("openid profile"), `
    [uri]::EscapeDataString("mosip:idp:acr:generated-code"), `
    [uri]::EscapeDataString($pkce.CodeChallenge), `
    [uri]::EscapeDataString($pkce.CodeChallengeMethod)

$summary = [ordered]@{
    esignetUi = $UiUrl
    esignetApi = $BaseUrl
    mockIdentityApi = $MockIdentityUrl
    clientId = $ClientId
    redirectUri = $RedirectUri
    authorizeUrl = $authorizeUrl
    codeVerifier = $pkce.CodeVerifier
    codeChallenge = $pkce.CodeChallenge
    loginMethod = "OTP"
    mockOtp = "111111"
    individualId = $IndividualId
    passwordLogin = "Passw0rd!"
    phone = "+251911223344"
    email = "amina.demo@example.com"
}

$summaryPath = Join-Path -Path $PSScriptRoot -ChildPath "last-demo-flow.json"
$authorizeUrlPath = Join-Path -Path $PSScriptRoot -ChildPath "last-authorize-url.txt"
$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath
$authorizeUrl | Set-Content -Path $authorizeUrlPath

Write-Host ""
Write-Host "Open this URL in your browser:" -ForegroundColor Green
Write-Host $authorizeUrl -ForegroundColor Cyan
Write-Host ""
Write-Host "The raw URL is also saved to:" -ForegroundColor Green
Write-Host $authorizeUrlPath -ForegroundColor Cyan
Write-Host "The full JSON summary is saved to:" -ForegroundColor Green
Write-Host $summaryPath -ForegroundColor Cyan
Write-Host ""
Write-Host "Use these login details:" -ForegroundColor Green
Write-Host "  individualId: $IndividualId"
Write-Host "  OTP: 111111"
Write-Host ""
