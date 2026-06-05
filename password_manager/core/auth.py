"""
Módulo de Autenticação - IronVault
----------------------------------
Responsável pelo Ciclo de Vida do Utilizador, Segurança de Sessão e Dead Man's Switch.
Implementa Argon2id com Pepper, Hardened Sessions e Transações Atómicas.
"""

import os
import time
import secrets
import gc
from datetime import datetime, timedelta
from collections import defaultdict
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHash
from dotenv import load_dotenv
from core.database import get_db_connection, get_db_connection_read

# --- CONFIGURAÇÕES E CONSTANTES ---
load_dotenv()

PEPPER = os.getenv('PEPPER')
if not PEPPER:
    raise Exception("ERRO CRÍTICO: Pepper não definido no ficheiro .env")

# Argon2id: Parâmetros resistentes a ataques de GPU e ASICs
ph = PasswordHasher(
    time_cost=2,          
    memory_cost=102400,    # 100 MB
    parallelism=8,         
    hash_len=32            
)

# Rate Limiting (Proteção Anti-Brute Force)
failed_attempts = defaultdict(list)
MAX_ATTEMPTS = 3
BLOCK_TIME = 300  # 5 minutos

# --- PROTEÇÃO CONTRA FORÇA BRUTA ---

def _is_blocked(username):
    """Verifica se o utilizador atingiu o limite de tentativas falhadas."""
    now = time.time()
    attempts = failed_attempts.get(username, [])
    # Filtra apenas tentativas dentro da janela de tempo ativa
    attempts = [t for t in attempts if (now - t[0]) < BLOCK_TIME]
    failed_attempts[username] = attempts
    
    if len(attempts) >= MAX_ATTEMPTS:
        return True
    return False

def _register_failed_attempt(username):
    """Regista uma nova falha no rate limiter."""
    failed_attempts[username].append((time.time(), 1))

# --- CRIPTOGRAFIA DE PASSWORDS ---

def hash_password(password):
    """Aplica Pepper e Argon2id. Limpa a memória após o processo."""
    peppered = password + PEPPER
    try:
        return ph.hash(peppered)
    finally:
        # CORREÇÃO: Sobreposição de memória para limpar o rasto da password
        peppered = "0" * len(peppered)
        del peppered
        gc.collect()

def verify_password(password, hash):
    """Valida a password contra o hash Argon2id."""
    peppered = password + PEPPER
    try:
        return ph.verify(hash, peppered)
    except (VerificationError, InvalidHash):
        return False
    finally:
        peppered = "0" * len(peppered)
        del peppered
        gc.collect()

# --- AUDITORIA ---

def _log_security_event(username, event_type, details, ip_address=None):
    """Regista eventos críticos para análise forense futura."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO security_logs (username, event_type, details, ip_address)
            VALUES (?, ?, ?, ?)
        ''', (username, event_type, details, ip_address))
        # Commit automático pelo context manager configurado no database.py

# --- GESTÃO DE SESSÕES (HARDENED) ---

def _create_session(user_id, ip_address, user_agent):
    """
    Cria uma nova sessão e invalida fisicamente todas as anteriores.
    CORREÇÃO: Implementa Hard Delete para evitar Session Fixation.
    """
    session_id = secrets.token_urlsafe(32)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Expulsa sessões concorrentes
        cursor.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
        
        # Cria nova sessão única
        cursor.execute('''
            INSERT INTO active_sessions (session_id, user_id, ip_address, user_agent, is_current)
            VALUES (?, ?, ?, ?, 1)
        ''', (session_id, user_id, ip_address, user_agent))
    return session_id

def validate_session(session_id, user_id):
    """Valida o token de sessão e atualiza a atividade."""
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_current FROM active_sessions 
            WHERE session_id = ? AND user_id = ?
        ''', (session_id, user_id))
        row = cursor.fetchone()
        
        if row and row['is_current'] == 1:
            cursor.execute('''
                UPDATE active_sessions SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
            return True
    return False

def invalidate_session(session_id):
    """CORREÇÃO: Remove fisicamente a sessão da base de dados (Logout Real)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM active_sessions WHERE session_id = ?', (session_id,))

# --- LOGICA DE LOGIN E MODO PÂNICO ---

def login(username, master_password, ip_address="127.0.0.1", user_agent="GUI"):
    """
    Fluxo de autenticação centralizado e protegido contra Race Conditions.
    """
    # 1. Verificar bloqueio preventivo (Rate Limiting)
    if _is_blocked(username):
        return None, None, "Acesso temporariamente bloqueado. Aguarde 5 minutos."

    # 2. Procurar utilizador (leitura simples — não bloqueia escritas)
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, master_password_hash, panic_password_hash 
            FROM users WHERE username = ?
        ''', (username,))
        user = cursor.fetchone()

    if not user:
        _register_failed_attempt(username)
        return None, None, "Credenciais inválidas."

    # 3. Lógica de Pânico (Dissimulação)
    # Verificamos primeiro se a senha inserida é a de pânico
    if user['panic_password_hash'] and verify_password(master_password, user['panic_password_hash']):
        _log_security_event(username, "panic_login", "Login sob coação detetado", ip_address)
        # Retorna PANIC_MODE para a GUI carregar o cofre falso
        return user['id'], None, "PANIC_MODE"

    # 4. Lógica de Master Password (Acesso Real)
    if verify_password(master_password, user['master_password_hash']):
        # Verificação do Dead Man's Switch (Verifica se o cofre está bloqueado)
        acesso, msg_bloqueio = verificar_estado_cofre(user['id'])
        
        if not acesso:
            # Se bloqueado, fingimos que a senha está errada para não dar pistas ao intruso
            _log_security_event(username, "master_login_blocked", msg_bloqueio, ip_address)
            _register_failed_attempt(username)
            return None, None, "Credenciais inválidas."

        # Login bem-sucedido: Limpar tentativas e criar sessão
        failed_attempts.pop(username, None)
        session_id = _create_session(user['id'], ip_address, user_agent)
        _log_security_event(username, "login_success", "Acesso concedido", ip_address)
        return user['id'], session_id, None

    # 5. Se nenhuma senha coincidir
    _register_failed_attempt(username)
    _log_security_event(username, "login_failed", "Tentativa de login inválida", ip_address)
    return None, None, "Credenciais inválidas."


# --- DEAD MAN'S SWITCH (LOGICA ATÓMICA) ---

def verificar_estado_cofre(user_id: int) -> tuple:
    """
    Analisa se o cofre deve ser bloqueado por falha de check-in.
    CORREÇÃO: Implementação atómica para evitar Race Conditions.
    """
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT panic_activated_at, restore_deadline, last_checkin, missed_checkins FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row or not row['panic_activated_at']:
            return True, ""

        agora = datetime.now()
        deadline = datetime.fromisoformat(row['restore_deadline'])

        # Bloqueio por tempo
        if agora > deadline:
            return False, "Bloqueio preventivo: Prazo de restauro expirado."

        # Bloqueio por falha de 'prova de vida'
        if row['missed_checkins'] >= 3:
            return False, "Bloqueio preventivo: Falhas de check-in."

        return True, ""
    
# ------------------------------------------------------------
# OBTENÇÃO DO IP DO CLIENTE (Audit Log Helper)
# ------------------------------------------------------------
def get_client_ip():
    """
    Tenta obter o IP real do cliente para registo em logs de segurança.
    Em ambiente de execução local (GUI), retorna geralmente 127.0.0.1.
    """
    import socket
    try:
        # Tenta obter o IP da interface de rede ativa
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
    
# ------------------------------------------------------------
# FUNÇÕES AUXILIARES DE UTILIZADOR
# ------------------------------------------------------------

# ------------------------------------------------------------
# GESTÃO GLOBAL DE SESSÕES E UTILIZADORES
# ------------------------------------------------------------

def invalidate_all_sessions(user_id, except_session=None):
    """
    Remove fisicamente todas as sessões de um utilizador da base de dados.
    Essencial após a recuperação de conta ou troca de master password.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if except_session:
            cursor.execute('''
                DELETE FROM active_sessions 
                WHERE user_id = ? AND session_id != ?
            ''', (user_id, except_session))
        else:
            cursor.execute('DELETE FROM active_sessions WHERE user_id = ?', (user_id,))
        # commit automático pelo context manager — não é necessário chamar explicitamente

def username_from_id(user_id):
    """Retorna o username associado a um ID de utilizador."""
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return row['username'] if row else "Desconhecido"

def verify_master_password(user_id, password):
    """Verifica a master password para reautenticação em operações críticas."""
    with get_db_connection_read() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT master_password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return verify_password(password, row['master_password_hash'])
        return False

# ------------------------------------------------------------
# REGISTO DE NOVOS UTILIZADORES
# ------------------------------------------------------------

def register(username, master_password, recovery_email, panic_password=None):
    """
    Regista um novo utilizador na base de dados.
    Retorna True em caso de sucesso, False se o username já existir ou ocorrer erro.
    """
    try:
        master_hash = hash_password(master_password)
        panic_hash = hash_password(panic_password) if panic_password else None

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, master_password_hash, panic_password_hash, recovery_email)
                VALUES (?, ?, ?, ?)
            ''', (username, master_hash, panic_hash, recovery_email))
        return True
    except Exception:
        return False

def fazer_checkin(user_id: int) -> bool:
    """
    Regista um check-in do utilizador para o Dead Man's Switch.
    Reinicia o contador de check-ins falhados e atualiza o timestamp.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET last_checkin   = CURRENT_TIMESTAMP,
                    missed_checkins = 0
                WHERE id = ?
            """, (user_id,))
            return cursor.rowcount > 0
    except Exception:
        return False


def activate_panic_mode(user_id: int) -> bool:
    """
    Ativa o Modo Pânico para o utilizador.
    Bloqueia o cofre real e regista o timestamp de ativação.
    Todas as sessões ativas são invalidadas imediatamente.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET panic_activated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_id,))

        invalidate_all_sessions(user_id)
        _log_security_event(
            username_from_id(user_id),
            "panic_mode_activated",
            "Modo Pânico ativado pelo utilizador"
        )
        return True
    except Exception:
        return False
