param(
    [string]$BaseUrl = "http://localhost:8088",
    [string]$UiUrl = "http://localhost:3000",
    [string]$MockIdentityUrl = "http://localhost:8082",
    [string]$ClientId = "",
    [string]$RedirectUri = "http://localhost:5555/callback",
    [string]$IndividualId = "7777888899"
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

function Get-DemoPersonas {
    @(
        [ordered]@{
            individualId = "5860356276"
            pin = "1234"
            email = "amina.demo@example.com"
            phone = "+251911223344"
            fullName = "Amina Hassan"
            nickName = "Amina"
            givenName = "Amina"
            middleName = "K"
            familyName = "Hassan"
            gender = "Female"
            dateOfBirth = "1996/04/03"
            streetAddress = "Kebribeyah Camp"
            locality = "Jijiga"
            region = "Somali"
            postalCode = "1000"
            country = "Ethiopia"
            password = "Passw0rd!"
            preferredLang = "eng"
            locale = "en"
            zoneInfo = "EAT"
            usage = "Seeded in RefuPass and used by the current Inji issuance demo."
        }
        [ordered]@{
            individualId = "5555444433"
            pin = "1234"
            email = "sami.demo@example.com"
            phone = "+251911334455"
            fullName = "Sami Bekele"
            nickName = "Sami"
            givenName = "Sami"
            middleName = "T"
            familyName = "Bekele"
            gender = "Male"
            dateOfBirth = "1994/09/12"
            streetAddress = "Jijiga Transit Site"
            locality = "Jijiga"
            region = "Somali"
            postalCode = "1000"
            country = "Ethiopia"
            password = "Passw0rd!"
            preferredLang = "eng"
            locale = "en"
            zoneInfo = "EAT"
            usage = "Seeded in RefuPass as the second shared person."
        }
        [ordered]@{
            individualId = "7777888899"
            pin = "1234"
            email = "nura.demo@example.com"
            phone = "+251900123456"
            fullName = "Nura Ali"
            nickName = "Nura"
            givenName = "Nura"
            middleName = "M"
            familyName = "Ali"
            gender = "Female"
            dateOfBirth = "1998/07/21"
            streetAddress = "Kebribeyah Camp"
            locality = "Jijiga"
            region = "Somali"
            postalCode = "1000"
            country = "Ethiopia"
            password = "Passw0rd!"
            preferredLang = "eng"
            locale = "en"
            zoneInfo = "EAT"
            usage = "Not seeded in RefuPass. Use this one to test Verify with eSignet in the web UI."
        }
    )
}

function Ensure-MockIdentity {
    param(
        [string]$MockIdentityUrl,
        [System.Collections.IDictionary]$Persona
    )

    if (Test-MockIdentityExists -MockIdentityUrl $MockIdentityUrl -IndividualId $Persona.individualId) {
        return
    }

    $userBody = @{
        requestTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        request = @{
            individualId = $Persona.individualId
            pin = $Persona.pin
            email = $Persona.email
            phone = $Persona.phone
            fullName = @(@{ language = "eng"; value = $Persona.fullName })
            nickName = @(@{ language = "eng"; value = $Persona.nickName })
            preferredUsername = @(@{ language = "eng"; value = $Persona.fullName })
            givenName = @(@{ language = "eng"; value = $Persona.givenName })
            middleName = @(@{ language = "eng"; value = $Persona.middleName })
            familyName = @(@{ language = "eng"; value = $Persona.familyName })
            gender = @(@{ language = "eng"; value = $Persona.gender })
            dateOfBirth = $Persona.dateOfBirth
            streetAddress = @(@{ language = "eng"; value = $Persona.streetAddress })
            locality = @(@{ language = "eng"; value = $Persona.locality })
            password = $Persona.password
            preferredLang = $Persona.preferredLang
            locale = $Persona.locale
            region = @(@{ language = "eng"; value = $Persona.region })
            zoneInfo = $Persona.zoneInfo
            postalCode = $Persona.postalCode
            country = @(@{ language = "eng"; value = $Persona.country })
            encodedPhoto = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
        }
    }

    $null = Invoke-RestMethod `
        -Method POST `
        -Uri "$MockIdentityUrl/v1/mock-identity-system/identity" `
        -ContentType "application/json" `
        -Body ($userBody | ConvertTo-Json -Depth 20 -Compress)

    if (-not (Test-MockIdentityExists -MockIdentityUrl $MockIdentityUrl -IndividualId $Persona.individualId)) {
        throw "Mock identity creation did not produce a usable identity for '$($Persona.individualId)'."
    }
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

$personas = Get-DemoPersonas
$selectedPersona = $personas | Where-Object { $_.individualId -eq $IndividualId } | Select-Object -First 1
if (-not $selectedPersona) {
    throw "No demo persona is defined for IndividualId '$IndividualId'."
}

foreach ($persona in $personas) {
    Ensure-MockIdentity -MockIdentityUrl $MockIdentityUrl -Persona $persona
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
    individualId = $selectedPersona.individualId
    passwordLogin = $selectedPersona.password
    phone = $selectedPersona.phone
    email = $selectedPersona.email
    fullName = $selectedPersona.fullName
    usage = $selectedPersona.usage
    personas = $personas
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
Write-Host "  individualId: $($selectedPersona.individualId)"
Write-Host "  OTP: 111111"
Write-Host ""
Write-Host "Available demo personas:" -ForegroundColor Green
foreach ($persona in $personas) {
    Write-Host "  $($persona.fullName) :: $($persona.individualId) :: $($persona.usage)"
}
Write-Host ""
