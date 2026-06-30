# GUIA DE DEPLOY - RAILWAY
## ORION General Agent v5.0

---

## 📋 PASSOS

### 1. Criar Repositório GitHub

1. Vá a **https://github.com/new**
2. Nome: **orion-general**
3. Visibilidade: **Private** (recomendado)
4. Toque em **"Create repository"**

---

### 2. Enviar Código para GitHub

No PowerShell:

```powershell
cd "C:\Users\BIG_P\OneDrive\Área de Trabalho\Ai\Jogo"

git init
git add .
git commit -m "ORION General Agent v5.0"
git remote add origin https://github.com/SEU_USER/orion-general.git
git push -u origin main
```

---

### 3. Criar Projeto no Railway

1. Vá a **https://railway.app/new**
2. Toque em **"Deploy from GitHub"**
3. Escolha o repositório **orion-general**
4. Railway detecta automaticamente

---

### 4. Configurar Variáveis

No Railway, vá a **Variables** e adicione:

```
PYTHON_VERSION=3.12
```

---

### 5. Deploy

1. Railway faz deploy automaticamente
2. Espere ~2-3 minutos
3. Toque no link gerado (ex: `orion.up.railway.app`)

---

## 📱 INSTALAR NO TELEMÓVEL

1. Abra o link no Chrome
2. Toque nos 3 pontos (⋮)
3. Selecione **"Adicionar ao ecrã inicial"**
4. Pronto!

---

## ⚠️ NOTA IMPORTANTE

O ORION precisa de carregar todos os módulos Python.
O primeiro deploy pode demorar 3-5 minutos.

---

## 🔧 PROBLEMAS COMUNS

| Problema | Solução |
|----------|---------|
| Deploy falha | Verificar logs no Railway |
| App não responde | Aguardar 2-3 min após deploy |
| Erro Python | Verificar requirements_cloud.txt |

---

*Guia criado por ORION General Agent v5.0*
