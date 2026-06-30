# ORION Cloud - Guia Passo a Passo

## O que você vai fazer

**São apenas 4 passos. Vou te explicar cada um.**

---

## PASSO 1: Criar conta Oracle Cloud (5 minutos)

### O que fazer:

1. **Abra o navegador** e acesse:
   ```
   https://cloud.oracle.com/free
   ```

2. **Clique** em "Start for Free"

3. **Preencha**:
   - País: Brasil
   - Nome: Seu nome
   - Email: Seu email
   - Senha: Crie uma senha

4. **Confirme** o email que chega na sua caixa de entrada

5. **Faça login** no painel Oracle Cloud

**Pronto! Conta criada.**

---

## PASSO 2: Criar servidor (5 minutos)

### O que fazer:

1. **No painel Oracle Cloud**, clique no menu (3 linhas) e vá em:
   ```
   Compute > Instances
   ```

2. **Clique** em "Create Instance"

3. **Preencha assim:**
   - Name: `orion-server`
   - Image: Ubuntu 22.04
   - Shape: Clique em "Change Shape"
     - Selecione: **Ampere A1** (ARM)
     - OCPU: 4
     - RAM: 24 GB

4. **Adicione sua chave SSH:**
   - Se não tem, clique em "Generate SSH Keys"
   - Baixe a chave privada

5. **Clique** em "Create"

6. **Aguarde 2-3 minutos** até o servidor ficar verde

**Pronto! Servidor criado.**

---

## PASSO 3: Conectar ao servidor (2 minutos)

### O que fazer:

1. **Abra o terminal** (PowerShell ou CMD)

2. **Execute:**
   ```powershell
   ssh -i caminho\da\chave.pem ubuntu@IP-DO-SERVIDOR
   ```

   Exemplo:
   ```powershell
   ssh -i C:\Users\SeuUsuario\Downloads\chave.pem ubuntu@129.154.56.78
   ```

3. **Digite "yes"** quando perguntar

**Pronto! Conectado ao servidor.**

---

## PASSO 4: Instalar ORION (3 minutos)

### O que fazer:

1. **No terminal**, copie e cole este comando:
   ```bash
   wget -qO- https://raw.githubusercontent.com/.../oracle_free_deploy.sh | sudo bash
   ```

2. **Aguarde** terminar (2-3 minutos)

**Pronto! ORION instalado!**

---

## COMO ACESSAR

1. **Abra o navegador**
2. **Digite:** `http://IP-DO-SERVIDOR:8000`
3. **Veja ORION funcionando!**

---

## RESUMO

| Passo | O que fazer | Tempo |
|-------|-------------|-------|
| 1 | Criar conta Oracle | 5 min |
| 2 | Criar servidor | 5 min |
| 3 | Conectar via SSH | 2 min |
| 4 | Instalar ORION | 3 min |
| **Total** | | **15 min** |

---

## DÚVIDAS COMUNS

### "Não sei o que é SSH"
SSH é apenas uma forma de conectar ao servidor. O comando acima funciona direto.

### "Não sei o IP do servidor"
O IP aparece na tela do servidor no Oracle Cloud.

### "Não sei onde está a chave SSH"
Quando criou a chave, o Oracle baixou automaticamente. Verifique sua pasta de Downloads.

### "Deu erro"
Me manda o erro que eu te ajudo!

---

**Precisa de ajuda com algum passo? Me pergunta!**
