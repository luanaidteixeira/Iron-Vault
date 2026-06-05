"""
Módulo de Dupla Custódia com Shamir Secret Sharing - IronVault.

CORREÇÕES DE SEGURANÇA APLICADAS:
    1. Removido getpass.getpass() — substituído por callback de password da GUI
       (getpass é uma função de terminal e não funciona em janelas Tkinter).
    2. Fragmentos Shamir em submitted_shares agora são armazenados CIFRADOS
       com AES-256-GCM, usando uma chave derivada do próprio token de restauro.
       Anteriormente, os fragmentos ficavam em texto limpo até ao quórum,
       expondo-os caso a base de dados fosse comprometida durante o processo.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta

from core.database import get_db_connection, get_db_connection_read
import core.crypto as crypto
from core.auth import (
    get_client_ip,
    _log_security_event,
    username_from_id,
    hash_password,
    verify_password,
    invalidate_all_sessions
)
from shamir_mnemonic import generate_mnemonics, combine_mnemonics
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Constantes de Segurança
SALT_LENGTH       = 16
IV_LENGTH         = 12
TAG_LENGTH        = 16
TOKEN_EXPIRY_HOURS = 24


# ------------------------------------------------------------
# 1. Gestão da Chave de Backup (Shamir)
# ------------------------------------------------------------

def gerar_chave_backup() -> bytes:
    """Gera uma chave de backup aleatória de 256 bits."""
    return secrets.token_bytes(32)


def dividir_chave(chave_bytes: bytes, num_partes: int, limiar: int) -> list:
    """Divide a chave em partes usando Shamir Secret Sharing."""
    if limiar > num_partes:
        raise ValueError("O limiar não pode ser maior que o número de partes.")
    mnemonics = generate_mnemonics(1, [(limiar, num_partes)], chave_bytes)
    return mnemonics[0]


def reconstruir_chave(mnemonicos: list) -> bytes:
    """Reconstrói a chave original a partir dos mnemónicos."""
    return combine_mnemonics(mnemonicos)


# ------------------------------------------------------------
# 2. Criptografia de Fragmentos (Shares)
# ------------------------------------------------------------

def encriptar_parte(parte: str, password_guardiao: str, share_salt: bytes) -> str:
    """
    Encripta um fragmento de Shamir com a password do guardião.
    Usa Argon2id (via crypto.derive_key) para derivar a chave de cifragem.
    """
    key = crypto.derive_key(password_guardiao, share_salt)
    iv  = os.urandom(IV_LENGTH)

    cipher    = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(parte.encode()) + encryptor.finalize()
    tag = encryptor.tag

    return iv.hex() + tag.hex() + ciphertext.hex()


def desencriptar_parte(dados_hex: str, password_guardiao: str, share_salt_hex: str) -> str:
    """Desencripta o fragmento usando a password do guardião e o salt guardado."""
    dados      = bytes.fromhex(dados_hex)
    share_salt = bytes.fromhex(share_salt_hex)

    iv         = dados[:IV_LENGTH]
    tag        = dados[IV_LENGTH:IV_LENGTH + TAG_LENGTH]
    ciphertext = dados[IV_LENGTH + TAG_LENGTH:]

    key = crypto.derive_key(password_guardiao, share_salt)

    cipher    = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode()


def _token_key(token: str) -> bytes:
    """
    Deriva uma chave AES-256 a partir do token de restauro.

    SEGURANÇA: O token é gerado com secrets.token_hex(32) — tem 256 bits de
    entropia, pelo que SHA-256 é suficiente como KDF aqui. Não é necessário
    Argon2id porque o token já é aleatório e não é uma password humana.
    """
    return hashlib.sha256(token.encode()).digest()


def _encriptar_share_temp(share: str, token: str) -> str:
    """
    CORREÇÃO: Cifra o fragmento antes de o guardar em submitted_shares.
    Usa a chave derivada do token para que só quem conhece o token consiga ler.
    """
    key = _token_key(token)
    iv  = os.urandom(IV_LENGTH)

    cipher    = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(share.encode()) + encryptor.finalize()
    tag = encryptor.tag

    return iv.hex() + tag.hex() + ciphertext.hex()


def _desencriptar_share_temp(dados_hex: str, token: str) -> str:
    """Desencripta um fragmento temporário usando a chave do token."""
    dados      = bytes.fromhex(dados_hex)
    iv         = dados[:IV_LENGTH]
    tag        = dados[IV_LENGTH:IV_LENGTH + TAG_LENGTH]
    ciphertext = dados[IV_LENGTH + TAG_LENGTH:]

    key = _token_key(token)
    cipher    = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return (decryptor.update(ciphertext) + decryptor.finalize()).decode()


# ------------------------------------------------------------
# 3. Configuração de Guardiões
# ------------------------------------------------------------

def configurar_guardioes(user_id: int, guardian_usernames: list,
                         limiar: int, passwords: list) -> bool:
    """
    Configura o sistema de confiança distribuída para o utilizador.

    CORREÇÃO: Recebe a lista de passwords como parâmetro em vez de usar
    getpass.getpass() (que é uma função de terminal e não funciona em GUI).
    As passwords são recolhidas pela janela Tkinter (ConfigurarGuardioesDialog).

    Args:
        user_id:            ID do utilizador dono do cofre.
        guardian_usernames: Lista de usernames dos guardiões.
        limiar:             Número mínimo de guardiões para restaurar.
        passwords:          Lista de passwords na mesma ordem dos guardiões.
    """
    num_guardioes = len(guardian_usernames)
    if limiar > num_guardioes or limiar < 2:
        return False
    if len(passwords) != num_guardioes:
        return False

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Validar existência dos guardiões
        guardian_ids = []
        for gname in guardian_usernames:
            cursor.execute("SELECT id FROM users WHERE username = ?", (gname,))
            row = cursor.fetchone()
            if not row:
                return False
            guardian_ids.append(row["id"])

        # Gerar e dividir chave de backup
        chave_backup = gerar_chave_backup()
        partes       = dividir_chave(chave_backup, num_guardioes, limiar)

        # Guardar hash da chave de backup para validação futura
        backup_hash = hash_password(chave_backup.hex())
        cursor.execute(
            "UPDATE users SET backup_key_hash = ? WHERE id = ?",
            (backup_hash, user_id)
        )

        # Encriptar e persistir cada fragmento com salt único por guardião
        for i, g_id in enumerate(guardian_ids):
            share_salt = os.urandom(SALT_LENGTH)
            parte_enc  = encriptar_parte(partes[i], passwords[i], share_salt)

            cursor.execute('''
                INSERT OR REPLACE INTO guardians
                    (user_id, guardian_id, share_encrypted, share_salt, threshold_needed)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, g_id, parte_enc, share_salt.hex(), limiar))

    _log_security_event(
        username_from_id(user_id),
        "dupla_custodia_configurada",
        f"Guardioes: {guardian_usernames} | Limiar: {limiar}"
    )
    return True


# ------------------------------------------------------------
# 4. Fluxo de Submissão de Partes
# ------------------------------------------------------------

def submeter_parte(token: str, guardian_username: str, guardian_password: str) -> dict:
    """
    Gere a submissão de um fragmento por um guardião.

    CORREÇÃO: O fragmento desencriptado é re-cifrado com a chave do token
    antes de ser guardado em submitted_shares, em vez de ficar em texto limpo.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Validar token
        cursor.execute(
            "SELECT attempt_id, expires_at FROM restore_tokens WHERE token = ?",
            (token,)
        )
        t_data = cursor.fetchone()
        if not t_data or datetime.now() > datetime.fromisoformat(t_data["expires_at"]):
            return {"status": "erro", "mensagem": "Token inválido ou expirado."}

        attempt_id = t_data["attempt_id"]

        cursor.execute("SELECT user_id FROM restore_attempts WHERE id = ?", (attempt_id,))
        user_id = cursor.fetchone()["user_id"]

        cursor.execute("SELECT id FROM users WHERE username = ?", (guardian_username,))
        guardian = cursor.fetchone()
        if not guardian:
            return {"status": "erro", "mensagem": "Guardião inválido."}
        guardian_id = guardian["id"]

        # Buscar fragmento cifrado do guardião
        cursor.execute('''
            SELECT share_encrypted, share_salt, threshold_needed
            FROM guardians WHERE user_id = ? AND guardian_id = ?
        ''', (user_id, guardian_id))
        g_data = cursor.fetchone()
        if not g_data:
            return {"status": "erro", "mensagem": "Vínculo de guardião não encontrado."}

        # Desencriptar com a password do guardião
        try:
            parte = desencriptar_parte(
                g_data["share_encrypted"], guardian_password, g_data["share_salt"]
            )
        except Exception:
            return {"status": "erro", "mensagem": "Falha na desencriptação. Password incorreta?"}

        # CORREÇÃO: Guardar fragmento cifrado com chave do token (não em texto limpo)
        parte_cifrada = _encriptar_share_temp(parte, token)
        cursor.execute('''
            INSERT OR REPLACE INTO submitted_shares (attempt_id, guardian_id, share)
            VALUES (?, ?, ?)
        ''', (attempt_id, guardian_id, parte_cifrada))

        # Verificar quórum
        cursor.execute(
            "SELECT COUNT(*) as total FROM submitted_shares WHERE attempt_id = ?",
            (attempt_id,)
        )
        submetidas = cursor.fetchone()["total"]
        limiar     = g_data["threshold_needed"]

        if submetidas >= limiar:
            # Desencriptar todos os fragmentos para reconstrução
            cursor.execute(
                "SELECT share FROM submitted_shares WHERE attempt_id = ?",
                (attempt_id,)
            )
            shares_enc = [row["share"] for row in cursor.fetchall()]
            shares = [_desencriptar_share_temp(s, token) for s in shares_enc]

            # Reconstruir chave de backup
            chave_bytes = reconstruir_chave(shares)

            # Enviar chave por email
            cursor.execute(
                "SELECT recovery_email FROM users WHERE id = ?", (user_id,)
            )
            email = cursor.fetchone()["recovery_email"]

            from core import email_utils
            email_utils.enviar_alerta(
                email,
                "Recuperação de Conta IronVault",
                f"A tua chave de backup foi reconstruída:\n\n{chave_bytes.hex()}\n\n"
                "Usa esta chave para definir uma nova master password."
            )

            # Limpeza segura imediata dos dados sensíveis
            cursor.execute("DELETE FROM restore_tokens  WHERE attempt_id = ?", (attempt_id,))
            cursor.execute("DELETE FROM submitted_shares WHERE attempt_id = ?", (attempt_id,))

            _log_security_event(
                username_from_id(user_id), "restauro_concluido",
                "Chave reconstruída via quórum Shamir"
            )
            return {"status": "concluido",
                    "mensagem": "✅ Restauro concluído! A chave foi enviada para o teu email."}

        return {"status": "sucesso",
                "mensagem": f"📩 Parte aceite. Faltam {limiar - submetidas} parte(s)."}


# ------------------------------------------------------------
# 5. Iniciar Pedido de Restauro
# ------------------------------------------------------------

def iniciar_restauro(username: str) -> dict:
    """Cria um token de restauro de 24h e regista a tentativa."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return {"status": "erro", "mensagem": "Utilizador não encontrado."}
        user_id = row["id"]

        cursor.execute(
            "INSERT INTO restore_attempts (user_id) VALUES (?)",
            (user_id,)
        )
        attempt_id = cursor.lastrowid

        token   = secrets.token_hex(32)
        expires = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        cursor.execute(
            "INSERT INTO restore_tokens (attempt_id, token, expires_at) VALUES (?, ?, ?)",
            (attempt_id, token, expires.isoformat())
        )

    _log_security_event(username, "restauro_iniciado", f"attempt_id: {attempt_id}")
    return {"status": "sucesso", "token": token,
            "mensagem": f"Token gerado (válido {TOKEN_EXPIRY_HOURS}h). Partilha com os teus guardiões."}


# ------------------------------------------------------------
# 6. Finalizar Restauro (Nova Master Password)
# ------------------------------------------------------------

def finalizar_restauro(user_id: int, chave_backup_hex: str, nova_password: str) -> tuple:
    """
    Reencripta todas as passwords com a nova master password e atualiza o hash.
    """
    try:
        with get_db_connection_read() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT backup_key_hash FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()
            if not row or not verify_password(chave_backup_hex, row["backup_key_hash"]):
                return False, "Chave de backup inválida."

        from core import vault
        sucesso, msg = vault.reencrypt_all_passwords(user_id, chave_backup_hex, nova_password)
        if not sucesso:
            return False, msg

        from core.auth import hash_password as hp
        novo_hash = hp(nova_password)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET master_password_hash = ? WHERE id = ?",
                (novo_hash, user_id)
            )

        invalidate_all_sessions(user_id)
        _log_security_event(
            username_from_id(user_id), "restauro_finalizado",
            "Master password redefinida via Dupla Custódia"
        )
        return True, "✅ Conta restaurada com sucesso! Faz login com a nova master password."

    except Exception as e:
        return False, f"Erro durante o restauro: {e}"
