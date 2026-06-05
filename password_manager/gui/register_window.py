"""
Ecrã de Registo - IronVault.
"""

import tkinter as tk
from tkinter import messagebox
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.styles import *
from core import auth


class RegisterFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = tk.Frame(self, bg=COR_SUPERFICIE, padx=50, pady=40)
        card.grid(row=0, column=0)
        card.config(highlightthickness=1, highlightbackground=COR_BORDA)

        self._criar_widgets(card)

    def _criar_widgets(self, card):
        # Título
        tk.Label(card, text="Criar Conta", font=FONTE_TITULO,
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(anchor="w")
        tk.Label(card, text="Preenche os campos abaixo para registar a tua conta.",
                 font=FONTE_LABEL, bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack(anchor="w", pady=(4, 20))

        tk.Frame(card, bg=COR_BORDA, height=1).pack(fill="x", pady=(0, 24))

        # Campos
        campos = [
            ("Utilizador *", "entry_username", None),
            ("Master Password *", "entry_master", "*"),
            ("Confirmar Master Password *", "entry_confirm", "*"),
            ("Email de recuperação *", "entry_email", None),
            ("Panic Password (opcional)", "entry_panic", "*"),
        ]

        for label, attr, show in campos:
            self._campo(card, label, attr, show)
            tk.Frame(card, height=10, bg=COR_SUPERFICIE).pack()

        tk.Label(card, text="* campos obrigatórios",
                 font=("Segoe UI", 8), bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack(anchor="w")

        tk.Frame(card, height=20, bg=COR_SUPERFICIE).pack()

        # Botões
        btn_frame = tk.Frame(card, bg=COR_SUPERFICIE)
        btn_frame.pack(fill="x")

        criar_botao(btn_frame, "Registar", self._registar, largura=14).pack(side="left", ipady=4)
        tk.Frame(btn_frame, width=10, bg=COR_SUPERFICIE).pack(side="left")
        criar_botao(btn_frame, "Voltar ao Login", self._voltar,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA).pack(side="left", ipady=4)

    def _campo(self, parent, label, attr, show=None):
        tk.Label(parent, text=label, font=("Segoe UI", 9, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x")
        tk.Frame(parent, height=4, bg=COR_SUPERFICIE).pack()
        entry = criar_entry(parent, show=show, largura=36)
        entry.pack(fill="x", ipady=6)
        setattr(self, attr, entry)

    def _registar(self):
        username = self.entry_username.get().strip()
        master   = self.entry_master.get().strip()
        confirm  = self.entry_confirm.get().strip()
        email    = self.entry_email.get().strip()
        panic    = self.entry_panic.get().strip() or None

        if not username:
            messagebox.showerror("Erro", "Utilizador é obrigatório."); return
        if not master:
            messagebox.showerror("Erro", "Master password é obrigatória."); return
        if master != confirm:
            messagebox.showerror("Erro", "As passwords não coincidem."); return
        if not email:
            messagebox.showerror("Erro", "Email de recuperação é obrigatório."); return
        if "@" not in email or "." not in email:
            messagebox.showerror("Erro", "Email inválido."); return

        if auth.register(username, master, email, panic):
            messagebox.showinfo("Sucesso", f"Conta '{username}' criada com sucesso!")
            self._limpar()
            self._voltar()
        else:
            messagebox.showerror("Erro", "Não foi possível registar. O utilizador já existe?")

    def _limpar(self):
        for attr in ("entry_username","entry_master","entry_confirm","entry_email","entry_panic"):
            getattr(self, attr).delete(0, tk.END)

    def _voltar(self):
        from gui.login_window import LoginFrame
        self.controller.mostrar_frame(LoginFrame)
