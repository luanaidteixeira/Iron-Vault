"""
Ecrã de Recuperação de Conta - IronVault.
Ativado após login com chave de backup (Dupla Custódia).
"""

import tkinter as tk
from tkinter import messagebox

from gui.styles import *
from gui.dialogs import PasswordDialog
from core import auth, dupla_custodia


class RecuperacaoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller  = controller
        self.user_id     = None
        self.session_id  = None
        self.username    = None
        self.chave_backup = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = tk.Frame(self, bg=COR_SUPERFICIE, padx=50, pady=40)
        card.grid(row=0, column=0)
        card.config(highlightthickness=1, highlightbackground=COR_BORDA)

        self._criar_widgets(card)

    def _criar_widgets(self, card):
        # Ícone + título
        tk.Label(card, text="🔓", font=("Segoe UI", 36),
                 bg=COR_SUPERFICIE, fg=COR_SUCESSO).pack()

        self.lbl_titulo = tk.Label(card, text="Recuperação de Conta",
                                    font=FONTE_TITULO, bg=COR_SUPERFICIE, fg=COR_TEXTO)
        self.lbl_titulo.pack(pady=(8, 4))

        tk.Label(card, text="Autenticado com chave de backup (Dupla Custódia)",
                 font=FONTE_LABEL, bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack()

        tk.Frame(card, bg=COR_BORDA, height=1).pack(fill="x", pady=24)

        # Caixa informativa
        info = tk.Frame(card, bg=COR_CARD, padx=20, pady=14)
        info.pack(fill="x")
        info.config(highlightthickness=1, highlightbackground=COR_BORDA)

        tk.Label(info, text="O que vai acontecer:", font=("Segoe UI", 9, "bold"),
                 bg=COR_CARD, fg=COR_TEXTO, anchor="w").pack(fill="x")

        passos = [
            "1.  Defines uma nova Master Password",
            "2.  Todas as tuas passwords são reencriptadas automaticamente",
            "3.  A sessão é encerrada e podes fazer login normalmente",
        ]
        for p in passos:
            tk.Label(info, text=p, font=("Segoe UI", 9),
                     bg=COR_CARD, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x", pady=2)

        tk.Frame(card, height=24, bg=COR_SUPERFICIE).pack()

        # Botões
        btn_frame = tk.Frame(card, bg=COR_SUPERFICIE)
        btn_frame.pack(fill="x")

        criar_botao(btn_frame, "🔑  Definir Nova Master Password",
                    self._definir_password,
                    cor=COR_SUCESSO, cor_hover=COR_SUCESSO_HV,
                    padx=20, pady=7).pack(fill="x", ipady=2)

        tk.Frame(card, height=10, bg=COR_SUPERFICIE).pack()

        criar_botao(btn_frame, "Cancelar e voltar ao login",
                    self._cancelar,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA,
                    padx=20, pady=7).pack(fill="x", ipady=2)

    def set_user_data(self, user_id, session_id, username, chave_backup):
        self.user_id      = user_id
        self.session_id   = session_id
        self.username     = username
        self.chave_backup = chave_backup
        self.lbl_titulo.config(text=f"Recuperação — {username}")

    def _definir_password(self):
        dlg1 = PasswordDialog(self, "Nova master password:")
        self.wait_window(dlg1)
        if not dlg1.result: return

        dlg2 = PasswordDialog(self, "Confirma a nova master password:")
        self.wait_window(dlg2)
        if not dlg2.result: return

        if dlg1.result != dlg2.result:
            messagebox.showerror("Erro", "As passwords não coincidem."); return

        sucesso, msg = dupla_custodia.finalizar_restauro(
            self.user_id, self.chave_backup, dlg1.result)

        if sucesso:
            messagebox.showinfo("✅ Sucesso", msg)
            auth.invalidate_session(self.session_id)
            self.controller.logout()
        else:
            messagebox.showerror("Erro", msg)

    def _cancelar(self):
        auth.invalidate_session(self.session_id)
        self.controller.logout()
