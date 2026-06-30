# ORION - Guia Simples (Português)

## O que você precisa fazer

**Apenas 3 passos simples:**

### Passo 1: Criar conta Oracle Cloud (GRÁTIS)

1. Acesse: https://cloud.oracle.com/free
2. Clique "Start for Free"
3. Preencha seus dados
4. **Cartão de crédito é necessário apenas para verificação, NÃO será cobrado**
5. Verifique o email e faça login

### Passo 2: Criar servidor

1. No painel Oracle Cloud, vá em: **Compute > Instances**
2. Clique "Create Instance"
3. Preencha:
   - **Name**: `orion-server`
   - **Image**: Ubuntu 22.04
   - **Shape**: **Ampere A1** (ARM)
   - **OCPU**: 4
   - **RAM**: 24 GB
4. Adicione sua chave SSH
5. Clique "Create"
6. Aguarde 2-3 minutos

### Passo 3: Instalar ORION

Conecte ao servidor e execute:

```bash
ssh -i sua-chave.pem ubuntu@SEU-IP

wget -qO- https://raw.githubusercontent.com/.../oracle_free_deploy.sh | sudo bash
```

**Pronto!** ORION está rodando 24/7!

## Como acessar

Abra o navegador e acesse:
```
http://SEU-IP:8000
```

## Comandos úteis

```bash
# Verificar status
sudo systemctl status orion

# Ver logs
sudo journalctl -u orion -f

# Reiniciar
sudo systemctl restart orion
```

## Custo

**R$ 0,00** - Oracle Cloud Free Tier é sempre grátis!

## ORION agora roda sozinho

- Seu computador pode ficar desligado
- ORION continua trabalhando 24/7
- Você pode acessar de qualquer lugar
- Não interfere no seu computador

---

**Qualquer dúvida, estou aqui para ajudar!**
