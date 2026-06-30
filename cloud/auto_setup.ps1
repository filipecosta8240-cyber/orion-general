# ORION Auto-Setup
# Execute este script no Windows para configurar tudo
#
# Uso:
#   1. Crie a conta Oracle Cloud (passo 1)
#   2. Crie o servidor (passo 2)
#   3. Execute este script
#   4. Siga as instruções

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ORION Auto-Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if SSH is available
$sshAvailable = Get-Command ssh -ErrorAction SilentlyContinue
if (-not $sshAvailable) {
    Write-Host "[ERRO] SSH nao encontrado!" -ForegroundColor Red
    Write-Host "Instale o OpenSSH:" -ForegroundColor Yellow
    Write-Host "  Configuracoes > Apps > Apps opcionais > Adicionar um recurso" -ForegroundColor Yellow
    Write-Host "  Instale ' cliente OpenSSH'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] SSH encontrado" -ForegroundColor Green
Write-Host ""

# Get server info
$serverIP = Read-Host "IP do servidor Oracle Cloud"
$keyPath = Read-Host "Caminho da chave SSH (ex: C:\Users\ usuario\Downloads\chave.pem)"

if (-not $serverIP -or -not $keyPath) {
    Write-Host "[ERRO] Preencha todos os campos!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testando conexao..." -ForegroundColor Yellow

# Test SSH connection
$result = ssh -i $keyPath -o ConnectTimeout=5 -o BatchMode=yes ubuntu@$serverIP "echo ok" 2>&1
if ($result -eq "ok") {
    Write-Host "[OK] Conexao SSH funcionando!" -ForegroundColor Green
} else {
    Write-Host "[AVISO] Nao foi possivel testar SSH" -ForegroundColor Yellow
    Write-Host "  Verifique se a chave esta correta" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Iniciando instalacao do ORION..." -ForegroundColor Cyan
Write-Host ""

# Upload and run deploy script
Write-Host "1. Enviando script de deploy..." -ForegroundColor Yellow
scp -i $keyPath "$PSScriptRoot\oracle_free_deploy.sh" ubuntu@${serverIP}:/tmp/

Write-Host "2. Executando deploy no servidor..." -ForegroundColor Yellow
ssh -i $keyPath ubuntu@$serverIP "sudo bash /tmp/orion_free_deploy.sh"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ORION Instalado com Sucesso!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Acesse ORION em:" -ForegroundColor Cyan
Write-Host "  http://${serverIP}:8000" -ForegroundColor White
Write-Host ""
Write-Host "Para configurar seu computador local:" -ForegroundColor Yellow
Write-Host "  bash setup_remote.sh" -ForegroundColor White
Write-Host ""
