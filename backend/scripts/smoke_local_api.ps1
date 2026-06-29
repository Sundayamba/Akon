param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-AkonJson {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Method,

        [Parameter(Mandatory = $true)]
        [string]$Uri,

        [object]$Body = $null,

        [hashtable]$Headers = @{}
    )

    $params = @{
        Method      = $Method
        Uri         = $Uri
        Headers     = $Headers
        ErrorAction = "Stop"
    }

    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 10)
    }

    return Invoke-RestMethod @params
}

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$email = "rex.smoke.$timestamp@example.com"
$password = "strongpassword123"
$displayName = "Rex Smoke"

Write-Host ""
Write-Host "Akon Local API Smoke Test" -ForegroundColor Green
Write-Host "Base URL: $BaseUrl"
Write-Host "Smoke user: $email"

Write-Step "Checking /health"
$health = Invoke-AkonJson -Method "GET" -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 10

if ($health.status -ne "ok") {
    throw "Health check failed."
}

Write-Step "Checking /version"
$version = Invoke-AkonJson -Method "GET" -Uri "$BaseUrl/version"
$version | ConvertTo-Json -Depth 10

Write-Step "Registering smoke user"
$registeredUser = Invoke-AkonJson `
    -Method "POST" `
    -Uri "$BaseUrl/auth/register" `
    -Body @{
        email        = $email
        password     = $password
        display_name = $displayName
    }

$registeredUser | ConvertTo-Json -Depth 10

if ($registeredUser.email -ne $email) {
    throw "Registration returned unexpected email."
}

Write-Step "Logging in smoke user"
$login = Invoke-AkonJson `
    -Method "POST" `
    -Uri "$BaseUrl/auth/login" `
    -Body @{
        email    = $email
        password = $password
    }

$loginSafe = @{
    token_type = $login.token_type
    expires_in = $login.expires_in
    user_email = $login.user.email
    has_access_token = -not [string]::IsNullOrWhiteSpace($login.access_token)
}

$loginSafe | ConvertTo-Json -Depth 10

if ([string]::IsNullOrWhiteSpace($login.access_token)) {
    throw "Login did not return an access token."
}

$authHeaders = @{
    Authorization = "Bearer $($login.access_token)"
}

Write-Step "Checking /auth/me"
$me = Invoke-AkonJson `
    -Method "GET" `
    -Uri "$BaseUrl/auth/me" `
    -Headers $authHeaders

$me | ConvertTo-Json -Depth 10

if ($me.email -ne $email) {
    throw "/auth/me returned unexpected user."
}

Write-Step "Creating memory"
$memory = Invoke-AkonJson `
    -Method "POST" `
    -Uri "$BaseUrl/memory" `
    -Headers $authHeaders `
    -Body @{
        memory_type   = "preference"
        content       = "Smoke user prefers direct, step-by-step guidance."
        source        = "local_smoke_test"
        confidence    = "high"
        sensitivity   = "low"
        consent_state = "explicit"
    }

$memory | ConvertTo-Json -Depth 10

if ([string]::IsNullOrWhiteSpace($memory.id)) {
    throw "Memory creation did not return an ID."
}

Write-Step "Listing memories"
$memories = Invoke-AkonJson `
    -Method "GET" `
    -Uri "$BaseUrl/memory" `
    -Headers $authHeaders

$memories | ConvertTo-Json -Depth 10

if ($memories.Count -lt 1) {
    throw "Memory list is empty after creating memory."
}

Write-Step "Sending chat message"
$chat = Invoke-AkonJson `
    -Method "POST" `
    -Uri "$BaseUrl/chat/message" `
    -Headers $authHeaders `
    -Body @{
        message = "I feel overwhelmed and need guidance."
    }

$chat | ConvertTo-Json -Depth 10

if ([string]::IsNullOrWhiteSpace($chat.conversation_id)) {
    throw "Chat response did not return a conversation ID."
}

Write-Step "Listing conversations"
$conversations = Invoke-AkonJson `
    -Method "GET" `
    -Uri "$BaseUrl/chat/conversations" `
    -Headers $authHeaders

$conversations | ConvertTo-Json -Depth 10

if ($conversations.Count -lt 1) {
    throw "Conversation list is empty after sending chat message."
}

Write-Step "Reading conversation detail"
$conversationDetail = Invoke-AkonJson `
    -Method "GET" `
    -Uri "$BaseUrl/chat/conversations/$($chat.conversation_id)" `
    -Headers $authHeaders

$conversationDetail | ConvertTo-Json -Depth 10

if ($conversationDetail.messages.Count -lt 2) {
    throw "Conversation detail did not return user and assistant messages."
}

Write-Step "Listing audit logs"
$auditLogs = Invoke-AkonJson `
    -Method "GET" `
    -Uri "$BaseUrl/audit" `
    -Headers $authHeaders

$auditLogs | ConvertTo-Json -Depth 10

if ($auditLogs.Count -lt 1) {
    throw "Audit log list is empty after smoke workflow."
}

Write-Host ""
Write-Host "Akon local API smoke test passed." -ForegroundColor Green
Write-Host ""