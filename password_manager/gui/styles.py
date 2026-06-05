"""
Módulo de estilos para a interface gráfica - IronVault.
Tema escuro profissional inspirado em aplicações de segurança modernas.
"""

import tkinter as tk
from tkinter import ttk

# ── PALETA DE CORES ──────────────────────────────────────────────
COR_FUNDO        = "#0f1117"   # Fundo principal (quase preto)
COR_SUPERFICIE   = "#1a1d2e"   # Cards e painéis
COR_CARD         = "#252840"   # Elementos elevados
COR_BORDA        = "#2e3354"   # Bordas subtis

COR_PRINCIPAL    = "#6366f1"   # Indigo (ação principal)
COR_PRINCIPAL_HV = "#4f52d4"   # Indigo hover
COR_DESTAQUE     = "#06b6d4"   # Cyan (destaque secundário)
COR_SECUNDARIA   = "#2e3354"   # Botão neutro

COR_SUCESSO      = "#10b981"   # Verde esmeralda
COR_SUCESSO_HV   = "#059669"
COR_ERRO         = "#ef4444"   # Vermelho
COR_ERRO_HV      = "#dc2626"
COR_AVISO        = "#f59e0b"   # Âmbar
COR_AVISO_HV     = "#d97706"

COR_TEXTO        = "#e2e8f0"   # Texto principal (quase branco)
COR_TEXTO_DIM    = "#94a3b8"   # Texto secundário (cinza azulado)
COR_TEXTO_CLARO  = "#ffffff"   # Branco puro

# ── FONTES ───────────────────────────────────────────────────────
FONTE_PADRAO    = ("Segoe UI", 10)
FONTE_TITULO    = ("Segoe UI", 18, "bold")
FONTE_SUBTITULO = ("Segoe UI", 12)
FONTE_BOTAO     = ("Segoe UI", 10, "bold")
FONTE_LABEL     = ("Segoe UI", 9)
FONTE_MONO      = ("Consolas", 10)
FONTE_BRAND     = ("Segoe UI", 28, "bold")


# ── HELPER: BOTÃO COM HOVER ──────────────────────────────────────
def criar_botao(parent, texto, comando, cor=None, cor_hover=None,
                largura=None, altura=1, padx=20, pady=8):
    """Cria um botão flat com efeito hover."""
    cor = cor or COR_PRINCIPAL
    cor_hover = cor_hover or COR_PRINCIPAL_HV

    kwargs = dict(
        text=texto,
        command=comando,
        bg=cor,
        fg=COR_TEXTO_CLARO,
        font=FONTE_BOTAO,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=padx,
        pady=pady,
        activebackground=cor_hover,
        activeforeground=COR_TEXTO_CLARO,
    )
    if largura:
        kwargs["width"] = largura

    btn = tk.Button(parent, **kwargs)
    btn.bind("<Enter>", lambda e: btn.config(bg=cor_hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=cor))
    return btn


def criar_entry(parent, show=None, largura=30):
    """Cria um campo de entrada estilizado."""
    e = tk.Entry(
        parent,
        show=show,
        font=FONTE_PADRAO,
        width=largura,
        bg=COR_CARD,
        fg=COR_TEXTO,
        insertbackground=COR_TEXTO,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightcolor=COR_PRINCIPAL,
        highlightbackground=COR_BORDA,
    )
    return e


def configurar_ttk():
    """Configura os estilos ttk globais (Treeview, Scrollbar)."""
    style = ttk.Style()
    style.theme_use("clam")

    # Treeview
    style.configure("Custom.Treeview",
        background=COR_SUPERFICIE,
        foreground=COR_TEXTO,
        fieldbackground=COR_SUPERFICIE,
        rowheight=34,
        font=("Segoe UI", 10),
        borderwidth=0,
    )
    style.configure("Custom.Treeview.Heading",
        background=COR_CARD,
        foreground=COR_TEXTO_DIM,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        borderwidth=0,
        padding=(10, 8),
    )
    style.map("Custom.Treeview",
        background=[("selected", COR_PRINCIPAL)],
        foreground=[("selected", COR_TEXTO_CLARO)],
    )
    style.map("Custom.Treeview.Heading",
        background=[("active", COR_BORDA)],
    )

    # Scrollbar
    style.configure("Custom.Vertical.TScrollbar",
        background=COR_CARD,
        troughcolor=COR_SUPERFICIE,
        arrowcolor=COR_TEXTO_DIM,
        borderwidth=0,
        width=8,
    )
