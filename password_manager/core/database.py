'''
Objetivo Geral:
    Este módulo é responsável por toda a comunicação com a base de dados SQLite.
    Foi corrigido para garantir que operações sensíveis (como Modo Pânico e Check-ins)
    sejam atómicas, prevenindo falhas de lógica em acessos simultâneos através de 
    transações imediatas (BEGIN IMMEDIATE).
'''

import sqlite3
from contextlib import contextmanager

# Nome do ficheiro da base de dados
DB_NOME = 'vault.db'

@contextmanager
def get_db_connection():
    """
    Context manager para gerir conexões à base de dados.
    CORREÇÃO DE SEGURANÇA: Utiliza 'BEGIN IMMEDIATE' para bloquear a escrita 
    concorrente desde o início da transação, mitigando Race Conditions.
    """
    # Timeout de 30 segundos para gerir filas de espera em acessos simultâneos
    conn = sqlite3.connect(DB_NOME, timeout=60)
    conn.row_factory = sqlite3.Row

    try:
        # Configurações de Integridade e Performance
        conn.execute("PRAGMA foreign_keys = ON") # Garante integridade referencial
        conn.execute("PRAGMA journal_mode = WAL") # Melhora a concorrência e desempenho
        
        # Inicia transação imediata para proteger a lógica de negócio crítica
        # Isto impede que dois processos leiam e alterem estados sensíveis ao mesmo tempo
        conn.execute("BEGIN IMMEDIATE")
        
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@contextmanager
def get_db_connection_read():
    """
    Context manager para conexões de LEITURA à base de dados.
    
    CORREÇÃO DE SEGURANÇA: Usa uma transação DEFERRED (padrão do SQLite) em vez
    de BEGIN IMMEDIATE. Queries de leitura não precisam de bloquear escritas
    concorrentes — BEGIN IMMEDIATE em leituras criava contenção desnecessária
    e degradava a performance em acessos simultâneos.
    Mantém WAL mode e foreign keys para consistência.
    """
    conn = sqlite3.connect(DB_NOME, timeout=60)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
    except Exception as e:
        raise e
    finally:
        conn.close()


def create_tables():
    """
    Cria todas as tabelas necessárias se elas ainda não existirem.
    Estrutura otimizada para segurança ofensiva, auditoria e resiliência.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Tabela de utilizadores (users)
        # Inclui estados para Dead Man's Switch e Modo Pânico
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                master_password_hash TEXT NOT NULL,
                panic_password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                recovery_email TEXT NOT NULL,
                panic_activated_at TIMESTAMP,
                restore_deadline TIMESTAMP,
                last_checkin TIMESTAMP,
                missed_checkins INTEGER DEFAULT 0,
                totp_secret TEXT,
                backup_key_hash TEXT,
                encryption_salt TEXT
                )
        ''')

        # 2. Tabela de passwords reais
        # Inclui flags para Honeypot (Iscos) e visibilidade em modo pânico
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                username TEXT,
                encrypted_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_honeypot INTEGER DEFAULT 0,
                show_in_panic INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # 3. Tabela de guardiões (Dupla Custódia)
        # CORREÇÃO: Adicionada a coluna 'share_salt' para entropia individual por fragmento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guardians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guardian_id INTEGER NOT NULL,
                share_encrypted TEXT NOT NULL,
                share_salt TEXT NOT NULL, 
                threshold_needed INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (guardian_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, guardian_id)
            )
        ''')

        # 4. Tabela de sessões ativas (Controlo de concorrência)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                is_current BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # 5. Tabelas para o processo de restauro (Dupla Custódia)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restore_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                location TEXT,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restore_tokens (
                attempt_id INTEGER PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES restore_attempts(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submitted_shares (
                attempt_id INTEGER NOT NULL,
                guardian_id INTEGER NOT NULL,
                share TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (attempt_id, guardian_id),
                FOREIGN KEY (attempt_id) REFERENCES restore_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (guardian_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # 6. Tabela de logs de segurança (Auditoria)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                event_type TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 7. Tabela de cofre falso (Modo Pânico)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fake_vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                username TEXT,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Índices de Performance para consultas rápidas
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_user ON passwords(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_current ON active_sessions(is_current)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_user ON security_logs(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_restore_token ON restore_tokens(token)')

        conn.commit()