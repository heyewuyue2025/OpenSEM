param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("strict","lite")]
  [string]$Mode,

  [string]$BaseUrl = "http://127.0.0.1:8020",

  [int]$TimeoutSec = 180,

  [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

function Assert-Command([string]$Name, [string]$Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "缺少命令：$Name。$Hint"
  }
}

function Compose-Down() {
  Write-Host "[docker] docker compose down"
  & docker compose down | Out-Host
}

function Compose-Up([hashtable]$Env, [switch]$Build) {
  $args = @("compose","up","-d")
  if ($Build) { $args += "--build" }

  $backup = @{}
  foreach ($k in $Env.Keys) {
    $existing = Get-Item -Path ("Env:" + $k) -ErrorAction SilentlyContinue
    $backup[$k] = if ($existing) { $existing.Value } else { $null }
    Set-Item -Path ("Env:" + $k) -Value ([string]$Env[$k])
  }

  try {
    Write-Host ("[docker] " + (($Env.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join " ") + " docker " + ($args -join " "))
    & docker @args | Out-Host
  } finally {
    foreach ($k in $Env.Keys) {
      if ($backup[$k] -eq $null) {
        Remove-Item Env:\$k -ErrorAction SilentlyContinue
      } else {
        Set-Item -Path ("Env:" + $k) -Value ([string]$backup[$k])
      }
    }
  }
}

function Get-Json([string]$Url) {
  return Invoke-RestMethod -Method GET -Uri $Url -TimeoutSec 20
}

function Wait-Health([string]$Url, [int]$TimeoutSec) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    try {
      $last = Get-Json $Url
      if ($null -ne $last -and $last.status -eq "healthy") {
        return $last
      }
    } catch {
      $last = $_.Exception.Message
    }
    Start-Sleep -Seconds 2
  }
  throw "等待健康检查超时（$TimeoutSec 秒）。最后一次结果：$last"
}

function Assert-HealthShape($health) {
  # 约束：health 必须返回这些字段，避免接口不小心改坏但脚本仍误判通过
  Require-True ($null -ne $health.status) "health 缺少 status 字段"
  Require-True ($null -ne $health.mode) "health 缺少 mode 字段"
  Require-True ($null -ne $health.require_lavaan) "health 缺少 require_lavaan 字段"
  Require-True ($null -ne $health.with_lavaan) "health 缺少 with_lavaan 字段"
  Require-True ($null -ne $health.lavaan) "health 缺少 lavaan 字段"
  Require-True ($null -ne $health.lavaan.available) "health 缺少 lavaan.available 字段"
 }

function Require-True([bool]$Cond, [string]$Msg) {
  if (-not $Cond) { throw $Msg }
}

Assert-Command "docker" "请先安装 Docker Desktop 并确保 docker 可用。"
Assert-Command "python" "strict 模式会调用 python e2e 脚本；请安装 Python 3。"

$build = -not $NoBuild

if ($Mode -eq "strict") {
  $envVars = @{
    "OPENSEM_WITH_LAVAAN"    = "1"
    "OPENSEM_REQUIRE_LAVAAN" = "1"
  }
} else {
  $envVars = @{
    "OPENSEM_WITH_LAVAAN"    = "0"
    "OPENSEM_REQUIRE_LAVAAN" = "0"
  }
}

Compose-Up -Env $envVars -Build:$build

$healthUrl = ($BaseUrl.TrimEnd("/") + "/api/health")
Write-Host "[check] waiting for /api/health ..."
$health = Wait-Health -Url $healthUrl -TimeoutSec $TimeoutSec

Write-Host "[ok] health=" ($health | ConvertTo-Json -Depth 8)
Assert-HealthShape $health

# Observability sanity checks (added in M2)
Write-Host "[check] request_id header + /api/metrics ..."
$healthResp = Invoke-WebRequest -UseBasicParsing -Method GET -Uri $healthUrl -TimeoutSec 20
if (-not $healthResp.Headers["X-Request-Id"]) {
  throw "health 响应缺少 X-Request-Id 头（观测性回归）"
}

$metricsUrl = ($BaseUrl.TrimEnd("/") + "/api/metrics")
$metricsBody = (Invoke-WebRequest -UseBasicParsing -Method GET -Uri $metricsUrl -TimeoutSec 20).Content
if ($metricsBody -notmatch "requests_total") {
  throw "/api/metrics 返回内容不包含 requests_total（观测性回归）"
}
Write-Host "[ok] metrics ok"

if ($Mode -eq "strict") {
  if ($health.mode -ne "strict") {
    Write-Host "[warn] 当前运行模式与期望不一致，尝试 docker compose down 后重启一次 ..."
    Compose-Down
    Compose-Up -Env $envVars -Build:$build
    $health = Wait-Health -Url $healthUrl -TimeoutSec $TimeoutSec
    Write-Host "[ok] health(after restart)=" ($health | ConvertTo-Json -Depth 8)
  }
  Require-True ($health.mode -eq "strict") "strict 模式下 health.mode 应为 strict，实际：$($health.mode)"
  Require-True ($health.require_lavaan -eq $true) "strict 模式下 require_lavaan 应为 true"
  Require-True ($health.lavaan.available -eq $true) "strict 模式下 lavaan.available 应为 true（否则说明 R/lavaan/rpy2 未装好）"

  Write-Host "[e2e] running backend/scripts/e2e_lavaan_api.py ..."
  $env:OPENSEM_BASE_URL = $BaseUrl.TrimEnd("/")
  & python ".\backend\scripts\e2e_lavaan_api.py"
  if ($LASTEXITCODE -ne 0) { throw "e2e 脚本失败，exit_code=$LASTEXITCODE" }
  Write-Host "[ok] strict e2e passed"
} else {
  if ($health.mode -ne "lite") {
    Write-Host "[warn] 当前运行模式与期望不一致，尝试 docker compose down 后重启一次 ..."
    Compose-Down
    Compose-Up -Env $envVars -Build:$build
    $health = Wait-Health -Url $healthUrl -TimeoutSec $TimeoutSec
    Write-Host "[ok] health(after restart)=" ($health | ConvertTo-Json -Depth 8)
  }
  Require-True ($health.mode -eq "lite") "lite 模式下 health.mode 应为 lite，实际：$($health.mode)"
  Require-True ($health.require_lavaan -eq $false) "lite 模式下 require_lavaan 应为 false"
  Write-Host "[e2e] running backend/scripts/e2e_phase1_lite_api.py (Phase 1 acceptance) ..."
  $env:OPENSEM_BASE_URL = $BaseUrl.TrimEnd("/")
  & python ".\backend\scripts\e2e_phase1_lite_api.py"
  if ($LASTEXITCODE -ne 0) { throw "lite e2e 脚本失败，exit_code=$LASTEXITCODE" }
  Write-Host "[ok] Phase 1 lite acceptance passed"
}

