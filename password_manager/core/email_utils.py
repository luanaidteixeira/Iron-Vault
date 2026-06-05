"""
Módulo para envio de emails de alerta.
Suporta dois modos:
  - Simulação: apenas imprime no terminal (útil para testes).
  - Real: envia email via SMTP (requer configuração no .env).
A escolha é feita pela variável de ambiente EMAIL_SIMULATE (true/false).
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("EMAIL_PASS")

# Flag para simulação (true = apenas print, false = envia realmente)
SIMULATE = os.getenv("EMAIL_SIMULATE", "true").lower() == "true"


def send_alert_email(to_email: str, username: str) -> None:
    """
    Envia um email de alerta para o recovery_email do utilizador.
    Se SIMULATE for True, apenas imprime no terminal.
    Caso contrário, tenta enviar via SMTP com as credenciais fornecidas.

    Args:
        to_email (str): Endereço de email do destinatário.
        username (str): Nome do utilizador (para personalizar a mensagem).
    """
    subject = "🚨 Alerta de segurança - Password Manager"
    body = f"""
Olá {username},

Foi detetada uma tentativa de acesso à tua conta com a master password enquanto o modo pânico estava ativo.

Se foste tu sob coação, não te preocupes: o acesso foi bloqueado e o intruso viu apenas um cofre falso.

Se não foste tu, alguém pode estar a tentar aceder à tua conta. Verifica a segurança.

Mantém-te seguro,
A equipa do Password Manager
"""

    if SIMULATE:
        # Modo simulação: apenas imprime
        print("\n" + "="*50)
        print("📧 SIMULAÇÃO DE ENVIO DE EMAIL")
        print("="*50)
        print(f"Para: {to_email}")
        print(f"Assunto: {subject}")
        print("Corpo:")
        print(body)
        print("="*50 + "\n")
        return

    # Modo real: verifica se credenciais estão configuradas
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️  Email não configurado (EMAIL_USER ou EMAIL_PASS em falta). Alerta não enviado.")
        return

    # Constrói a mensagem
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Conecta ao servidor SMTP e envia
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"📧 Email de alerta enviado com sucesso para {to_email}.")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")

def enviar_alerta(to_email: str, assunto: str, corpo: str) -> None:
    """
    Envia um email genérico de alerta (usado pela Dupla Custódia e outros módulos).
    Se SIMULATE for True, apenas imprime no terminal.
    """
    if SIMULATE:
        print("\n" + "="*50)
        print("📧 SIMULAÇÃO DE ENVIO DE EMAIL")
        print("="*50)
        print(f"Para: {to_email}")
        print(f"Assunto: {assunto}")
        print(f"Corpo:\n{corpo}")
        print("="*50 + "\n")
        return

    if not SMTP_USER or not SMTP_PASS:
        print("⚠️  Email não configurado. Alerta não enviado.")
        return

    msg = MIMEMultipart()
    msg['From']    = SMTP_USER
    msg['To']      = to_email
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"📧 Email enviado para {to_email}.")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
