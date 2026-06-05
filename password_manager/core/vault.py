"""
Módulo de gestão do cofre de passwords - IronVault.
Gerencia as operações de CRUD, lógica de Honeypot e o Modo Pânico Persistente.
Inclui proteções contra análise forense e ataques de canal lateral.
"""

import os
import secrets
import string
import time
import gc
import pyperclip
from core.database import get_db_connection, get_db_connection_read
import core.crypto as crypto
from core.auth import invalidate_session, _log_security_event, get_client_ip

# --- CONSTANTES DE SEGURANÇA ---
DEFAULT_PASSWORD_LENGTH = 20
CLIPBOARD_CLEAR_DELAY = 15    # Minimiza janela de exposição para Side-Channel attacks
MIN_PANIC_PASSWORDS = 8       # Aumenta credibilidade estatística do cofre falso
PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*()"

# ------------------------------------------------------------
# 1. Gerador de Passwords e Gestão de Salt
# ------------------------------------------------------------

def generate_password(length: int = DEFAULT_PASSWORD_LENGTH) -> str:
    """Gera passwords usando a biblioteca 'secrets' (criptograficamente segura)."""
    return ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))

def _get_user_salt(user_id: int) -> bytes:
    """Obtém ou gera o salt individual do utilizador para a KDF."""
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT encryption_salt FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row['encryption_salt']:
            return bytes.fromhex(row['encryption_salt'])

    # Salt ainda não existe — gerar e persistir (requer escrita)
    salt = os.urandom(16)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET encryption_salt = ? WHERE id = ?", (salt.hex(), user_id))
    return salt

# ------------------------------------------------------------
# 2. Defesa Ativa e Higiene de Memória
# ------------------------------------------------------------

def _handle_honeypot_access(user_id: int, session_id: str, username: str, service: str) -> None:
    """Invalida a sessão instantaneamente após acesso a um Honeypot."""
    ip = get_client_ip()
    _log_security_event(username, "honeypot_triggered", f"Acesso a isca: {service}", ip)
    invalidate_session(session_id)

def clear_clipboard_securely():
    """Limpa a clipboard sobrepondo a memória com dados nulos."""
    pyperclip.copy(" " * 50) 
    time.sleep(0.1)
    pyperclip.copy("")
    gc.collect()

# ------------------------------------------------------------
# 3. Operações do Cofre Real
# ------------------------------------------------------------

def add_password(user_id: int, master_password: str, service: str, username: str,
                 plain_password: str = None, is_honeypot: bool = False, 
                 show_in_panic: bool = False):
    """Encripta e armazena uma nova credencial usando AES-256-GCM."""
    if not plain_password:
        plain_password = generate_password()

    salt = _get_user_salt(user_id)
    key = crypto.derive_key(master_password, salt)
    
    try:
        encrypted = crypto.encrypt_password(plain_password, key)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO passwords (user_id, service, username, encrypted_password, is_honeypot, show_in_panic)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, service, username, encrypted, 1 if is_honeypot else 0, 1 if show_in_panic else 0))
    finally:
        # Limpeza de variáveis sensíveis da RAM
        del key
        gc.collect()

def reencrypt_all_passwords(user_id: int, old_key_source: str, new_password: str) -> tuple:
    """
    Migra todas as passwords para uma nova chave (usado no restauro pós-pânico).
    Retorna (sucesso: bool, mensagem: str).
    """
    salt = _get_user_salt(user_id)
    # A old_key_source pode ser a chave de backup ou a master antiga
    old_key = crypto.derive_key(old_key_source, salt)
    new_key = crypto.derive_key(new_password, salt)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, encrypted_password FROM passwords WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()

            for row in rows:
                # Desencripta com a chave antiga e re-encripta com a nova
                decrypted = crypto.decrypt_password(row['encrypted_password'], old_key)
                reencrypted = crypto.encrypt_password(decrypted, new_key)
                
                cursor.execute("UPDATE passwords SET encrypted_password = ? WHERE id = ?", (reencrypted, row['id']))
        return True, "Cofre re-encriptado com sucesso."
    except Exception as e:
        return False, f"Falha na migração do cofre: {str(e)}"
    finally:
        del old_key
        del new_key
        gc.collect()

# ------------------------------------------------------------
# 4. Gestão do Cofre Falso (Modo Pânico Persistente)
# ------------------------------------------------------------

def _seed_fake_vault(user_id: int) -> None:
    """Cria o cofre falso com normalização de timestamps forenses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fake_timestamp = "2024-01-01 10:00:00"

        # 1. Metadados de contas reais permitidas ou iscos
        cursor.execute('''
            SELECT service, username FROM passwords 
            WHERE user_id = ? AND (show_in_panic = 1 OR is_honeypot = 1)
        ''', (user_id,))
        rows = cursor.fetchall()

        for row in rows:
            cursor.execute('''
                INSERT INTO fake_vault (user_id, service, username, password, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, row['service'], row['username'], '••••••••', fake_timestamp))

        # 2. Preenchimento de ruído estatístico
        if len(rows) < MIN_PANIC_PASSWORDS:
            extra = ["Netflix", "Amazon", "Twitter", "PayPal", "Gmail", "LinkedIn", "Spotify", "Dropbox"]
            for i in range(MIN_PANIC_PASSWORDS - len(rows)):
                cursor.execute('''
                    INSERT INTO fake_vault (user_id, service, username, password, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, extra[i % len(extra)], f"user_{i}@mail.com", '••••••••', fake_timestamp))

def get_fake_vault(user_id: int) -> list:
    """Retorna dados do cofre falso, gerando-os no primeiro acesso."""
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM fake_vault WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]

    if count == 0:
        _seed_fake_vault(user_id)

    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, service, username, password FROM fake_vault WHERE user_id = ? ORDER BY service ASC', (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_password(user_id: int, password_id: int) -> bool:
    """Remove uma credencial do cofre real do utilizador."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM passwords WHERE id = ? AND user_id = ?",
            (password_id, user_id)
        )
        return cursor.rowcount > 0


def delete_fake_password(user_id: int, password_id: int) -> bool:
    """Remove uma entrada do cofre falso (modo pânico)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM fake_vault WHERE id = ? AND user_id = ?",
            (password_id, user_id)
        )
        return cursor.rowcount > 0


def add_fake_password(user_id: int, service: str, username: str, password: str) -> bool:
    """Adiciona uma entrada ao cofre falso."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO fake_vault (user_id, service, username, password) VALUES (?, ?, ?, ?)",
            (user_id, service, username, password)
        )
        return cursor.rowcount > 0
