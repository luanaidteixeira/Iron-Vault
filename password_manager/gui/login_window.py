"""
Ecrã de Login - IronVault.
Design moderno com card centralizado e tema escuro.
"""

import tkinter as tk
from tkinter import messagebox
import sys, os, gc
from PIL import Image, ImageTk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.styles import *
from core import auth


class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        configurar_ttk()

        # Grid para centrar o card
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Card central
        card = tk.Frame(self, bg=COR_SUPERFICIE, padx=50, pady=40)
        card.grid(row=0, column=0)
        card.config(highlightthickness=1, highlightbackground=COR_BORDA)

        self._criar_widgets(card)

    def _criar_widgets(self, card):
        # ── Logo + Nome ──
        brand = tk.Frame(card, bg=COR_SUPERFICIE)
        brand.pack(pady=(0, 6))

        try:
            caminho = os.path.join(os.path.dirname(__file__), 'logo.png')
            img = Image.open(caminho).resize((42, 42), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(brand, image=self.logo_img, bg=COR_SUPERFICIE).pack(side="left", padx=(0, 10))
        except Exception:
            pass

        tk.Label(brand, text="IronVault", font=FONTE_BRAND,
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(side="left")

        tk.Label(card, text="Gestor de Passwords Seguro",
                 font=FONTE_LABEL, bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack(pady=(0, 30))

        # ── Separador ──
        tk.Frame(card, bg=COR_BORDA, height=1).pack(fill="x", pady=(0, 28))

        # ── Campos ──
        self._campo(card, "Utilizador", "entry_username")
        tk.Frame(card, height=12, bg=COR_SUPERFICIE).pack()
        self._campo(card, "Master Password", "entry_password", show="*")

        self.entry_password.bind("<Return>", lambda e: self._login())

        # ── Botões ──
        tk.Frame(card, height=28, bg=COR_SUPERFICIE).pack()

        btn_login = criar_botao(card, "Entrar", self._login, largura=28)
        btn_login.pack(fill="x", ipady=4)

        tk.Frame(card, height=10, bg=COR_SUPERFICIE).pack()

        btn_reg = criar_botao(card, "Criar conta", self._ir_registo,
                              cor=COR_SECUNDARIA, cor_hover=COR_BORDA, largura=28)
        btn_reg.pack(fill="x", ipady=4)

        # ── Rodapé ──
        tk.Frame(card, bg=COR_BORDA, height=1).pack(fill="x", pady=(28, 14))
        tk.Label(card, text="🔒  Todas as passwords são cifradas localmente com AES-256-GCM",
                 font=("Segoe UI", 8), bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack()

    def _campo(self, parent, label, attr, show=None):
        tk.Label(parent, text=label, font=("Segoe UI", 9, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x")
        tk.Frame(parent, height=4, bg=COR_SUPERFICIE).pack()
        entry = criar_entry(parent, show=show, largura=32)
        entry.pack(fill="x", ipady=6)
        setattr(self, attr, entry)

    def _login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        if not username or not password:
            messagebox.showerror("Erro", "Preenche todos os campos.")
            return

        user_id, session_id, erro = auth.login(username, password, "127.0.0.1", "GUI")

        if user_id:
            self.entry_password.delete(0, tk.END)
            if erro == "PANIC_MODE":
                self.controller.login_panico(user_id, username)
            else:
                self.controller.login_sucesso(user_id, session_id, username, password)
        else:
            messagebox.showerror("Acesso Negado", erro)
            self.entry_password.delete(0, tk.END)

        gc.collect()

    def _ir_registo(self):
        self.entry_username.delete(0, tk.END)
        self.entry_password.delete(0, tk.END)
        from gui.register_window import RegisterFrame
        self.controller.mostrar_frame(RegisterFrame)
