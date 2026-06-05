"""
Módulo de Criptografia - IronVault
----------------------------------
Responsável pela derivação de chaves (KDF) e operações de cifragem autenticada.
Utiliza AES-256-GCM para garantir Confidencialidade e Integridade.

CORREÇÃO DE SEGURANÇA:
    Substituição de PBKDF2-HMAC-SHA256 por Argon2id para derivação de chave.
    O PBKDF2 é vulnerável a ataques com hardware especializado (GPUs/ASICs) porque
    opera apenas sobre CPU com consumo de memória mínimo.
    O Argon2id (vencedor do Password Hashing Competition) é resistente a esses
    ataques por design: força o atacante a usar grandes quantidades de memória RAM,
    tornando ataques paralelos economicamente inviáveis.
    Esta escolha é consistente com o Argon2id já usado na autenticação (auth.py),
    garantindo uniformidade criptográfica em todo o sistema.
"""

import os
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- CONSTANTES DE SEGURANÇA (Padrões NIST/OWASP) ---
IV_LENGTH  = 12   # 96 bits : Tamanho ideal para evitar colisões no modo GCM
TAG_LENGTH = 16   # 128 bits: Tag de autenticação robusta (selo de integridade)
KEY_LENGTH = 32   # 256 bits: Chave AES de nível máximo de segurança

# Parâmetros Argon2id para KDF (derivação de chave do cofre)
# Valores calibrados para resistência a ataques offline com GPU/ASIC:
#   - time_cost=3       : 3 iterações (aumenta custo de CPU)
#   - memory_cost=65536 : 64 MB de RAM obrigatórios por tentativa
#   - parallelism=2     : 2 threads paralelas
# Nota: memory_cost mais baixo que no login (102 400) é intencional —
# a KDF é chamada em cada operação do cofre; o equilíbrio entre
# segurança e usabilidade justifica este valor.
ARGON2_TIME_COST   = 3
ARGON2_MEMORY_COST = 65_536   # 64 MB
ARGON2_PARALLELISM = 2
ARGON2_HASH_LEN    = KEY_LENGTH
ARGON2_TYPE        = Type.ID   # Argon2id = proteção contra side-channel + GPU


def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Transforma a master password numa chave criptográfica de 256 bits (AES-256).

    SEGURANÇA:
        Argon2id exige 64 MB de RAM por tentativa, tornando ataques de força bruta
        com GPU/ASIC economicamente inviáveis. Um atacante com 1000 GPUs ainda
        precisaria de anos para testar o espaço de passwords comuns.

    Args:
        master_password: Password em texto limpo do utilizador.
        salt: Salt aleatório de 16 bytes único por utilizador (armazenado na DB).

    Returns:
        Chave de 32 bytes (256 bits) pronta para uso com AES-256-GCM.
    """
    key = hash_secret_raw(
        secret=master_password.encode(),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=ARGON2_TYPE,
    )
    return key


def encrypt_password(plaintext: str, key: bytes) -> str:
    """
    Encripta uma string usando AES-256-GCM (cifragem autenticada).

    Retorna uma string hexadecimal contendo: IV + TAG + CIPHERTEXT.
    O Tag é essencial para a 'Cifragem Autenticada', impedindo que um
    atacante altere bits do texto cifrado sem ser detetado (bit-flipping).

    Formato de saída: [IV — 24 hex chars][TAG — 32 hex chars][CIPHERTEXT — variável]
    """
    # IV aleatório único por operação — fundamental para segurança semântica
    # (duas passwords iguais produzem textos cifrados completamente diferentes)
    iv = os.urandom(IV_LENGTH)

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    tag = encryptor.tag  # Selo de integridade gerado pelo modo GCM

    return iv.hex() + tag.hex() + ciphertext.hex()


def decrypt_password(encrypted_data: str, key: bytes) -> str:
    """
    Desencripta e VALIDA a integridade dos dados através do Tag GCM.

    SEGURANÇA:
        Se o Tag for inválido (dados alterados ou chave errada), o modo GCM
        lança uma exceção imediata no finalize(), impedindo ataques de
        manipulação de bits (bit-flipping / padding oracle).
        A mensagem de erro é genérica para evitar Side-Channel/Oracle Attacks.
    """
    try:
        iv_hex         = encrypted_data[:IV_LENGTH * 2]
        tag_hex        = encrypted_data[IV_LENGTH * 2:(IV_LENGTH + TAG_LENGTH) * 2]
        ciphertext_hex = encrypted_data[(IV_LENGTH + TAG_LENGTH) * 2:]

        iv         = bytes.fromhex(iv_hex)
        tag        = bytes.fromhex(tag_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()

        plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext_bytes.decode()

    except Exception:
        raise Exception("Falha na desencriptação: Credenciais inválidas ou integridade violada.")
