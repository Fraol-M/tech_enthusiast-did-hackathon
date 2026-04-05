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

function New-DemoPersona {
    param(
        [string]$IndividualId,
        [string]$FullName,
        [string]$GivenName,
        [string]$MiddleName,
        [string]$FamilyName,
        [string]$Gender,
        [string]$DateOfBirth,
        [string]$Phone,
        [string]$Email,
        [string]$StreetAddress,
        [string]$Locality = "Jijiga",
        [string]$Region = "Somali",
        [string]$PostalCode = "1000",
        [string]$Country = "Ethiopia",
        [string]$Usage = "Not seeded in RefuPass. Use this identity to test Verify with eSignet in the web UI."
    )

    [ordered]@{
        individualId = $IndividualId
        pin = "1234"
        email = $Email
        phone = $Phone
        fullName = $FullName
        nickName = $GivenName
        givenName = $GivenName
        middleName = $MiddleName
        familyName = $FamilyName
        gender = $Gender
        dateOfBirth = $DateOfBirth
        streetAddress = $StreetAddress
        locality = $Locality
        region = $Region
        postalCode = $PostalCode
        country = $Country
        password = "Passw0rd!"
        preferredLang = "eng"
        locale = "en"
        zoneInfo = "EAT"
        usage = $Usage
    }
}

function Get-DemoPersonas {
    @(
        (New-DemoPersona -IndividualId "5860356276" -FullName "Amina Hassan" -GivenName "Amina" -MiddleName "K" -FamilyName "Hassan" -Gender "Female" -DateOfBirth "1996/04/03" -Phone "+251911223344" -Email "amina.demo@example.com" -StreetAddress "Kebribeyah Camp" -Usage "Seeded in RefuPass as the first shared person.")
        (New-DemoPersona -IndividualId "5555444433" -FullName "Sami Bekele" -GivenName "Sami" -MiddleName "T" -FamilyName "Bekele" -Gender "Male" -DateOfBirth "1994/09/12" -Phone "+251911334455" -Email "sami.demo@example.com" -StreetAddress "Jijiga Transit Site" -Usage "Seeded in RefuPass as the second shared person.")
        (New-DemoPersona -IndividualId "7777888899" -FullName "Nura Ali" -GivenName "Nura" -MiddleName "M" -FamilyName "Ali" -Gender "Female" -DateOfBirth "1998/07/21" -Phone "+251900123456" -Email "nura.demo@example.com" -StreetAddress "Kebribeyah Camp")
        (New-DemoPersona -IndividualId "7777888801" -FullName "Rahma Yusuf" -GivenName "Rahma" -MiddleName "A" -FamilyName "Yusuf" -Gender "Female" -DateOfBirth "1992/05/17" -Phone "+251900100001" -Email "rahma.demo@example.com" -StreetAddress "Kebribeyah Camp")
        (New-DemoPersona -IndividualId "7777888802" -FullName "Omar Aden" -GivenName "Omar" -MiddleName "H" -FamilyName "Aden" -Gender "Male" -DateOfBirth "1989/11/02" -Phone "+251900100002" -Email "omar.demo@example.com" -StreetAddress "Kebribeyah Camp")
        (New-DemoPersona -IndividualId "7777888803" -FullName "Hawa Noor" -GivenName "Hawa" -MiddleName "S" -FamilyName "Noor" -Gender "Female" -DateOfBirth "1990/03/28" -Phone "+251900100003" -Email "hawa.demo@example.com" -StreetAddress "Kebribeyah Camp")
        (New-DemoPersona -IndividualId "7777888804" -FullName "Abdi Farah" -GivenName "Abdi" -MiddleName "J" -FamilyName "Farah" -Gender "Male" -DateOfBirth "1995/01/14" -Phone "+251900100004" -Email "abdi.demo@example.com" -StreetAddress "Aw Barre Camp")
        (New-DemoPersona -IndividualId "7777888805" -FullName "Ifrah Ahmed" -GivenName "Ifrah" -MiddleName "M" -FamilyName "Ahmed" -Gender "Female" -DateOfBirth "1997/08/09" -Phone "+251900100005" -Email "ifrah.demo@example.com" -StreetAddress "Aw Barre Camp")
        (New-DemoPersona -IndividualId "7777888806" -FullName "Khalid Hassan" -GivenName "Khalid" -MiddleName "R" -FamilyName "Hassan" -Gender "Male" -DateOfBirth "1991/10/19" -Phone "+251900100006" -Email "khalid.demo@example.com" -StreetAddress "Aw Barre Camp")
        (New-DemoPersona -IndividualId "7777888807" -FullName "Asha Ibrahim" -GivenName "Asha" -MiddleName "D" -FamilyName "Ibrahim" -Gender "Female" -DateOfBirth "1999/02/22" -Phone "+251900100007" -Email "asha.demo@example.com" -StreetAddress "Sheder Camp")
        (New-DemoPersona -IndividualId "7777888808" -FullName "Mohamed Ali" -GivenName "Mohamed" -MiddleName "K" -FamilyName "Ali" -Gender "Male" -DateOfBirth "1988/06/11" -Phone "+251900100008" -Email "mohamed.demo@example.com" -StreetAddress "Sheder Camp")
        (New-DemoPersona -IndividualId "7777888809" -FullName "Safiya Osman" -GivenName "Safiya" -MiddleName "Y" -FamilyName "Osman" -Gender "Female" -DateOfBirth "1993/09/03" -Phone "+251900100009" -Email "safiya.demo@example.com" -StreetAddress "Sheder Camp")
        (New-DemoPersona -IndividualId "7777888810" -FullName "Jama Abdirahman" -GivenName "Jama" -MiddleName "L" -FamilyName "Abdirahman" -Gender "Male" -DateOfBirth "1996/12/18" -Phone "+251900100010" -Email "jama.demo@example.com" -StreetAddress "Melkadida Camp")
        (New-DemoPersona -IndividualId "7777888811" -FullName "Maryan Muse" -GivenName "Maryan" -MiddleName "H" -FamilyName "Muse" -Gender "Female" -DateOfBirth "1994/07/05" -Phone "+251900100011" -Email "maryan.demo@example.com" -StreetAddress "Melkadida Camp")
        (New-DemoPersona -IndividualId "7777888812" -FullName "Faisal Abdullahi" -GivenName "Faisal" -MiddleName "N" -FamilyName "Abdullahi" -Gender "Male" -DateOfBirth "1990/04/27" -Phone "+251900100012" -Email "faisal.demo@example.com" -StreetAddress "Melkadida Camp")
        (New-DemoPersona -IndividualId "7777888813" -FullName "Ubah Hassan" -GivenName "Ubah" -MiddleName "A" -FamilyName "Hassan" -Gender "Female" -DateOfBirth "1998/11/13" -Phone "+251900100013" -Email "ubah.demo@example.com" -StreetAddress "Hilaweyn Camp")
        (New-DemoPersona -IndividualId "7777888814" -FullName "Abukar Warsame" -GivenName "Abukar" -MiddleName "T" -FamilyName "Warsame" -Gender "Male" -DateOfBirth "1987/01/31" -Phone "+251900100014" -Email "abukar.demo@example.com" -StreetAddress "Hilaweyn Camp")
        (New-DemoPersona -IndividualId "7777888815" -FullName "Samira Ismail" -GivenName "Samira" -MiddleName "B" -FamilyName "Ismail" -Gender "Female" -DateOfBirth "1995/05/25" -Phone "+251900100015" -Email "samira.demo@example.com" -StreetAddress "Hilaweyn Camp")
        (New-DemoPersona -IndividualId "7777888816" -FullName "Yassin Adam" -GivenName "Yassin" -MiddleName "C" -FamilyName "Adam" -Gender "Male" -DateOfBirth "1992/03/15" -Phone "+251900100016" -Email "yassin.demo@example.com" -StreetAddress "Bokolmayo Camp")
        (New-DemoPersona -IndividualId "7777888817" -FullName "Hodan Nur" -GivenName "Hodan" -MiddleName "E" -FamilyName "Nur" -Gender "Female" -DateOfBirth "1991/08/20" -Phone "+251900100017" -Email "hodan.demo@example.com" -StreetAddress "Bokolmayo Camp")
        (New-DemoPersona -IndividualId "7777888818" -FullName "Mustafa Mohamud" -GivenName "Mustafa" -MiddleName "G" -FamilyName "Mohamud" -Gender "Male" -DateOfBirth "1989/10/07" -Phone "+251900100018" -Email "mustafa.demo@example.com" -StreetAddress "Bokolmayo Camp")
        (New-DemoPersona -IndividualId "7777888819" -FullName "Nasteho Jama" -GivenName "Nasteho" -MiddleName "I" -FamilyName "Jama" -Gender "Female" -DateOfBirth "1997/12/02" -Phone "+251900100019" -Email "nasteho.demo@example.com" -StreetAddress "Kule Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888820" -FullName "Ahmed Guled" -GivenName "Ahmed" -MiddleName "O" -FamilyName "Guled" -Gender "Male" -DateOfBirth "1993/02/08" -Phone "+251900100020" -Email "ahmed.guled.demo@example.com" -StreetAddress "Kule Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888821" -FullName "Fadumo Ali" -GivenName "Fadumo" -MiddleName "P" -FamilyName "Ali" -Gender "Female" -DateOfBirth "1996/06/30" -Phone "+251900100021" -Email "fadumo.demo@example.com" -StreetAddress "Tierkidi Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888822" -FullName "Tesfaye Bekele" -GivenName "Tesfaye" -MiddleName "Q" -FamilyName "Bekele" -Gender "Male" -DateOfBirth "1988/09/24" -Phone "+251900100022" -Email "tesfaye.demo@example.com" -StreetAddress "Tierkidi Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888823" -FullName "Aster Demissie" -GivenName "Aster" -MiddleName "R" -FamilyName "Demissie" -Gender "Female" -DateOfBirth "1990/01/12" -Phone "+251900100023" -Email "aster.demo@example.com" -StreetAddress "Pugnido Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888824" -FullName "Solomon Tadesse" -GivenName "Solomon" -MiddleName "S" -FamilyName "Tadesse" -Gender "Male" -DateOfBirth "1991/11/09" -Phone "+251900100024" -Email "solomon.demo@example.com" -StreetAddress "Pugnido Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888825" -FullName "Halima Ahmed" -GivenName "Halima" -MiddleName "T" -FamilyName "Ahmed" -Gender "Female" -DateOfBirth "1998/04/18" -Phone "+251900100025" -Email "halima.demo@example.com" -StreetAddress "Jewi Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888826" -FullName "Muktar Omar" -GivenName "Muktar" -MiddleName "U" -FamilyName "Omar" -Gender "Male" -DateOfBirth "1994/07/29" -Phone "+251900100026" -Email "muktar.demo@example.com" -StreetAddress "Jewi Camp" -Locality "Gambella" -Region "Gambella")
        (New-DemoPersona -IndividualId "7777888827" -FullName "Roda Abdi" -GivenName "Roda" -MiddleName "V" -FamilyName "Abdi" -Gender "Female" -DateOfBirth "1995/03/06" -Phone "+251900100027" -Email "roda.demo@example.com" -StreetAddress "Sherkole Camp" -Locality "Asosa" -Region "Benishangul-Gumuz")
        (New-DemoPersona -IndividualId "7777888828" -FullName "Bilal Osman" -GivenName "Bilal" -MiddleName "W" -FamilyName "Osman" -Gender "Male" -DateOfBirth "1992/08/14" -Phone "+251900100028" -Email "bilal.demo@example.com" -StreetAddress "Sherkole Camp" -Locality "Asosa" -Region "Benishangul-Gumuz")
        (New-DemoPersona -IndividualId "7777888829" -FullName "Fatuma Yusuf" -GivenName "Fatuma" -MiddleName "X" -FamilyName "Yusuf" -Gender "Female" -DateOfBirth "1997/10/26" -Phone "+251900100029" -Email "fatuma.demo@example.com" -StreetAddress "Bambasi Camp" -Locality "Asosa" -Region "Benishangul-Gumuz")
        (New-DemoPersona -IndividualId "7777888830" -FullName "Dawit Kassa" -GivenName "Dawit" -MiddleName "Y" -FamilyName "Kassa" -Gender "Male" -DateOfBirth "1993/05/04" -Phone "+251900100030" -Email "dawit.demo@example.com" -StreetAddress "Bambasi Camp" -Locality "Asosa" -Region "Benishangul-Gumuz")
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
