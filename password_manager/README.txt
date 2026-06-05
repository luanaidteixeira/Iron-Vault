# 🔐 IronVault — Password Manager

Gestor de passwords local com criptografia de nível profissional.  
Desenvolvido como Projeto Final do Curso de **Técnico Especialista em Cibersegurança — Nível 5**.

---

## ⚡ Instalação Rápida

### 1. Requisitos
- Python **3.11** ou superior
- Windows 10/11, macOS 12+ ou Linux (Ubuntu 20.04+)

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Iniciar a aplicação

```bash
python run.py
```

---

## 📁 Estrutura do Projeto

```
password_manager/
├── run.py                  # Ponto de entrada
├── requirements.txt        # Dependências Python
├── .env                    # Configurações secretas (PEPPER, email)
├── vault.db                # Base de dados cifrada (gerada automaticamente)
├── core/
│   ├── auth.py             # Autenticação (Argon2id + Pepper)
│   ├── crypto.py           # Criptografia (AES-256-GCM, Argon2id KDF)
│   ├── database.py         # Gestão da base de dados SQLite
│   ├── vault.py            # Gestão do cofre de passwords
│   ├── dupla_custodia.py   # Shamir Secret Sharing
│   └── email_utils.py      # Alertas por email
└── gui/
    ├── app.py              # Controlador principal (Tkinter)
    ├── styles.py           # Tema visual (dark mode)
    ├── login_window.py     # Ecrã de login
    ├── register_window.py  # Ecrã de registo
    ├── cofre_window.py     # Cofre real
    ├── cofre_falso_window.py # Cofre falso (Modo Pânico)
    ├── dialogs.py          # Diálogos partilhados
    └── dupla_custodia_config.py # Configuração de guardiões
```

---

## ⚙️ Configuração do ficheiro `.env`

```env
# Pepper — valor secreto global (mínimo 32 caracteres aleatórios)
PEPPER=coloca_aqui_um_valor_longo_e_aleatorio_de_pelo_menos_32_chars

# Email para alertas de segurança (opcional)
EMAIL_USER=teuemail@gmail.com
EMAIL_PASS=password_de_app_google
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# true = só mostra no terminal; false = envia email real
EMAIL_SIMULATE=true
```

> ⚠️ **Nunca partilhes o `.env`.** Sem ele, o acesso ao cofre é impossível.

---

## 🛡️ Funcionalidades de Segurança

| Funcionalidade | Implementação |
|---|---|
| Hashing de passwords | Argon2id + Pepper (OWASP recomendado) |
| Cifragem do cofre | AES-256-GCM com IV único por entrada |
| Derivação de chave | Argon2id (64 MB RAM por operação) |
| Proteção por coação | Modo Pânico com cofre falso |
| Recuperação distribuída | Shamir Secret Sharing (N de M guardiões) |
| Deteção de intrusão | Honeypots com audit log forense |
| Bloqueio automático | Dead Man's Switch com check-ins |
| Higiene de memória | Sobreposição de variáveis sensíveis + gc.collect() |
| Clipboard segura | Limpeza automática após 15 segundos |
| Anti-brute force | Rate limiting + bloqueio após 3 tentativas |

---

## 🚀 Primeiro Uso

1. Inicia a aplicação com `python run.py`
2. Clica em **"Criar conta"**
3. Define o teu username, master password e email de recuperação
4. (Opcional) Define uma **Panic Password** para o Modo Pânico
5. Faz login e começa a adicionar as tuas passwords

---

## 🔑 Modo Pânico

Se fores forçado a dar acesso ao cofre sob ameaça, usa a **Panic Password**.  
O sistema apresenta um cofre falso com entradas credíveis — o atacante não tem forma de perceber que é falso.

---

## 👥 Dupla Custódia

Permite recuperar o acesso ao cofre sem a master password, com a colaboração de guardiões de confiança.

1. Vai a **"👥 Guardiões"** no cofre
2. Indica os usernames dos guardiões e o limiar mínimo
3. Cada guardião define a sua password para selar o fragmento
4. Em caso de recuperação, os guardiões submetem o token + a sua password

---

## 📋 Dependências

```
Pillow          — Interface gráfica (imagens)
argon2-cffi     — Hashing Argon2id
cryptography    — AES-256-GCM
python-dotenv   — Variáveis de ambiente
pyperclip       — Clipboard segura
shamir-mnemonic — Shamir Secret Sharing
```

---

*IronVault — Projeto Final 2025/2026*