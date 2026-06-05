"""
Diálogo de configuração da Dupla Custódia - IronVault.
Recolhe as passwords dos guardiões via GUI (substituindo getpass).
"""

import tkinter as tk
from tkinter import messagebox

from gui.styles import *
from gui.dialogs import PasswordDialog, _centrar
from core import dupla_custodia


class ConfigurarGuardioesDialog(tk.Toplevel):
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.title("Dupla Custódia")
        self.configure(bg=COR_SUPERFICIE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.user_id = user_id

        _centrar(self, parent, 520, 420)
        self._criar_widgets()

    def _criar_widgets(self):
        # Título
        tk.Label(self, text="👥  Configurar Dupla Custódia",
                 font=("Segoe UI", 13, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(pady=(24, 4), padx=30, anchor="w")
        tk.Label(self,
                 text="Define quem pode ajudar a recuperar o teu cofre em caso de emergência.",
                 font=FONTE_LABEL, bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack(padx=30, anchor="w")

        tk.Frame(self, bg=COR_BORDA, height=1).pack(fill="x", padx=30, pady=(16, 20))

        f = tk.Frame(self, bg=COR_SUPERFICIE, padx=30)
        f.pack(fill="x")

        # Campo guardiões
        tk.Label(f, text="Guardiões (usernames separados por vírgula) *",
                 font=("Segoe UI", 9, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x")
        tk.Frame(f, height=4, bg=COR_SUPERFICIE).pack()
        self.entry_guardioes = criar_entry(f, largura=50)
        self.entry_guardioes.pack(fill="x", ipady=6)
        tk.Label(f, text="Exemplo:  ana, joao, maria",
                 font=("Segoe UI", 8, "italic"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x", pady=(4, 0))

        tk.Frame(f, height=16, bg=COR_SUPERFICIE).pack()

        # Limiar
        tk.Label(f, text="Mínimo de guardiões para restaurar o acesso *",
                 font=("Segoe UI", 9, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x")
        tk.Frame(f, height=4, bg=COR_SUPERFICIE).pack()

        spin_frame = tk.Frame(f, bg=COR_SUPERFICIE)
        spin_frame.pack(anchor="w")

        self.limiar_var = tk.IntVar(value=2)
        spin = tk.Spinbox(spin_frame, from_=1, to=10,
                          textvariable=self.limiar_var,
                          font=FONTE_PADRAO, width=6,
                          bg=COR_CARD, fg=COR_TEXTO,
                          buttonbackground=COR_BORDA,
                          relief="flat", bd=1,
                          highlightthickness=1,
                          highlightbackground=COR_BORDA,
                          highlightcolor=COR_PRINCIPAL)
        spin.pack(side="left", ipady=5)
        tk.Label(spin_frame,
                 text="  (ex: 2 de 3 guardiões precisam de colaborar)",
                 font=("Segoe UI", 8, "italic"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack(side="left")

        # Caixa informativa
        tk.Frame(f, height=16, bg=COR_SUPERFICIE).pack()
        info = tk.Frame(f, bg=COR_CARD, padx=14, pady=10)
        info.pack(fill="x")
        info.config(highlightthickness=1, highlightbackground=COR_BORDA)
        tk.Label(info,
                 text="ℹ️  No passo seguinte, será pedida a password de cada guardião\n"
                      "para selar o seu fragmento de forma segura.",
                 font=("Segoe UI", 8), bg=COR_CARD, fg=COR_TEXTO_DIM,
                 justify="left", anchor="w").pack(fill="x")

        # Botões
        tk.Frame(self, bg=COR_BORDA, height=1).pack(fill="x", padx=30, pady=(20, 0))
        btn_f = tk.Frame(self, bg=COR_SUPERFICIE, pady=16)
        btn_f.pack()

        criar_botao(btn_f, "Configurar", self._guardar,
                    padx=20, pady=5).pack(side="left", padx=8)
        criar_botao(btn_f, "Cancelar", self.destroy,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA,
                    padx=20, pady=5).pack(side="left", padx=8)

    def _guardar(self):
        entrada = self.entry_guardioes.get().strip()
        if not entrada:
            messagebox.showerror("Erro", "Indica pelo menos um guardião.", parent=self)
            return

        guardioes = [g.strip() for g in entrada.split(",") if g.strip()]
        if len(guardioes) < 2:
            messagebox.showerror("Erro", "É necessário pelo menos 2 guardiões.", parent=self)
            return

        limiar = self.limiar_var.get()
        if limiar < 1 or limiar > len(guardioes):
            messagebox.showerror("Erro",
                f"O limiar deve estar entre 1 e {len(guardioes)}.", parent=self)
            return

        # Recolher passwords de cada guardião via GUI (substitui getpass)
        passwords = []
        for nome in guardioes:
            dlg = PasswordDialog(self, f"Password de '{nome}' para selar o fragmento:")
            self.wait_window(dlg)
            if not dlg.result:
                messagebox.showwarning("Cancelado",
                    "Configuração cancelada — todos os guardiões precisam de submeter a password.",
                    parent=self)
                return
            passwords.append(dlg.result)

        sucesso = dupla_custodia.configurar_guardioes(
            self.user_id, guardioes, limiar, passwords)

        if sucesso:
            messagebox.showinfo("✅ Sucesso",
                "Dupla Custódia configurada com sucesso!\n"
                "Cada guardião recebeu o seu fragmento selado.", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Erro",
                "Falha na configuração.\n"
                "Verifica se todos os guardiões estão registados.", parent=self)
