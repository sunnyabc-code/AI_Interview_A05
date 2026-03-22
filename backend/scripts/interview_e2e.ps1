param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [ValidateSet('email','phone')][string]$LoginType = 'email',
    [Parameter(Mandatory = $true)][string]$Identifier,
    [Parameter(Mandatory = $true)][string]$Password,
    [int]$RoundsToRun = 3,
    [string]$DifficultyCode = 'easy',
    [int]$PositionId = 0,
    [switch]$EnableTechnical = $true,
    [switch]$EnableProject = $true,
    [switch]$EnableScenario = $false
)

$ErrorActionPreference = 'Stop'

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )

    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 8
        return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -ContentType 'application/json; charset=utf-8' -Body $json
    }

    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers
}

Write-Host '== 1) Login ==' -ForegroundColor Cyan
$loginResp = Invoke-Api -Method 'POST' -Url "$BaseUrl/api/users/login/" -Body @{
    login_type = $LoginType
    identifier = $Identifier
    password = $Password
}

if ($loginResp.code -ne 200) {
    throw "Login failed: $($loginResp | ConvertTo-Json -Depth 6)"
}

$token = $loginResp.data.access
$headers = @{ Authorization = "Bearer $token" }
Write-Host "Login success, user_id: $($loginResp.data.user.id)"

Write-Host '== 2) Fetch positions ==' -ForegroundColor Cyan
$positionsResp = Invoke-Api -Method 'GET' -Url "$BaseUrl/api/positions/" -Headers $headers
if ($positionsResp.code -ne 200 -or -not $positionsResp.data -or $positionsResp.data.Count -eq 0) {
    throw 'Position list is empty. Please seed position data first.'
}

$selectedPosition = $null
if ($PositionId -gt 0) {
    $selectedPosition = $positionsResp.data | Where-Object { $_.id -eq $PositionId } | Select-Object -First 1
    if ($null -eq $selectedPosition) {
        throw "Position ID not found: $PositionId"
    }
} else {
    $selectedPosition = $positionsResp.data | Select-Object -First 1
}
Write-Host "Using position: id=$($selectedPosition.id), name=$($selectedPosition.name)"

Write-Host '== 3) Fetch difficulty configs ==' -ForegroundColor Cyan
$diffResp = Invoke-Api -Method 'GET' -Url "$BaseUrl/api/evaluations/difficulty-configs/" -Headers $headers
if ($diffResp.code -ne 200 -or -not $diffResp.data -or $diffResp.data.Count -eq 0) {
    throw 'Difficulty config list is empty. Please seed difficulty config first.'
}

$selectedDiff = $diffResp.data | Where-Object { $_.difficulty_code -eq $DifficultyCode } | Select-Object -First 1
if ($null -eq $selectedDiff) {
    throw "Difficulty config not found: $DifficultyCode"
}
Write-Host "Using difficulty: id=$($selectedDiff.id), code=$($selectedDiff.difficulty_code)"

Write-Host '== 4) Create interview ==' -ForegroundColor Cyan
$createBody = @{
    position = $selectedPosition.id
    name = "e2e-interview-$((Get-Date).ToString('yyyyMMdd-HHmmss'))"
    mode = 'text'
    difficulty_config = $selectedDiff.id
    enable_technical_questions = [bool]$EnableTechnical
    enable_project_questions = [bool]$EnableProject
    enable_scenario_questions = [bool]$EnableScenario
    notes = 'created by e2e script'
}

$createResp = Invoke-Api -Method 'POST' -Url "$BaseUrl/api/v1/interviews/" -Headers $headers -Body $createBody
if ($createResp.code -ne 201) {
    throw "Create interview failed: $($createResp | ConvertTo-Json -Depth 8)"
}

$interviewId = $createResp.data.id
Write-Host "Interview created: interview_id=$interviewId"

$savedRoundIds = @()

for ($i = 1; $i -le $RoundsToRun; $i++) {
    Write-Host "== 5.$i) Get next question ==" -ForegroundColor Cyan
    $nextResp = Invoke-Api -Method 'POST' -Url "$BaseUrl/api/v1/interviews/$interviewId/next-question/" -Headers $headers -Body @{}

    if (($nextResp.code -ne 200) -and ($nextResp.code -ne 201)) {
        throw "Get next question failed: $($nextResp | ConvertTo-Json -Depth 8)"
    }

    $nextData = $nextResp.data

    if ($nextData.need_llm_generation -eq $true) {
        Write-Warning 'Question bank miss. API returned llm_prompt and did not create a round.'
        Write-Host "Prompt: $($nextData.llm_prompt)"
        throw 'Script stopped: seed question bank first, or make next-question auto-call LLM and persist round.'
    }

    $roundId = $nextData.round_id
    $savedRoundIds += $roundId

    Write-Host ("round_id={0}, round_number={1}, chain_index={2}, followup_depth={3}, category={4}" -f `
        $nextData.round_id, $nextData.round_number, $nextData.chain_index, $nextData.followup_depth, $nextData.category)
    Write-Host "question: $($nextData.question_content)"

    $answerText = "e2e answer for round $i at $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))"

    Write-Host "== 5.$i) Submit answer ==" -ForegroundColor Cyan
    $answerResp = Invoke-Api -Method 'POST' -Url "$BaseUrl/api/v1/interviews/$interviewId/rounds/$roundId/answer/" -Headers $headers -Body @{
        user_answer = $answerText
    }

    if ($answerResp.code -ne 200) {
        throw "Submit answer failed: $($answerResp | ConvertTo-Json -Depth 8)"
    }

    Write-Host ("Answer saved: round_id={0}, already_answered={1}, end_time={2}" -f `
        $answerResp.data.round_id, $answerResp.data.already_answered, $answerResp.data.end_time)
}

Write-Host '== 6) Interview detail ==' -ForegroundColor Cyan
$detailResp = Invoke-Api -Method 'GET' -Url "$BaseUrl/api/v1/interviews/$interviewId/" -Headers $headers
if ($detailResp.code -eq 200) {
    Write-Host "interview_status=$($detailResp.data.status), total_rounds=$($detailResp.data.total_rounds), start_time=$($detailResp.data.start_time)"
}

Write-Host '== 7) DB verification via Django ORM ==' -ForegroundColor Cyan
$pythonExpr = @"
from interviews.models import InterviewRound
rows = InterviewRound.objects.filter(interview_id=$interviewId).order_by('round_number').values('id','round_number','chain_index','followup_depth','question_content','user_answer','end_time')
print('round_count=', rows.count())
for r in rows:
    print(r)
"@

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..
$pythonPath = Join-Path (Resolve-Path ..) '.venv/Scripts/python.exe'
if (-not (Test-Path $pythonPath)) {
    $pythonPath = 'python'
}

& $pythonPath manage.py shell -c $pythonExpr

Write-Host '== E2E completed ==' -ForegroundColor Green
Write-Host "interview_id=$interviewId"
Write-Host "round_ids=$($savedRoundIds -join ',')"
