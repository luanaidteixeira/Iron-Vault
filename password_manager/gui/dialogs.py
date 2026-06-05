"""
Diálogos personalizados - IronVault.
"""

import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.styles import *
from core import vault


def _centrar(win, parent, w, h):
    win.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width()  - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


class PasswordDialog(tk.Toplevel):
    """Pede uma password com ocultação."""
    def __init__(self, parent, prompt):
        super().__init__(parent)
        self.title("Autenticação")
        self.configure(bg=COR_SUPERFICIE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        _centrar(self, parent, 360, 180)

        tk.Label(self, text="🔑  Confirmar Identidade", font=("Segoe UI", 11, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(pady=(24, 4))
        tk.Label(self, text=prompt, font=FONTE_LABEL,
                 bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM).pack()

        f = tk.Frame(self, bg=COR_SUPERFICIE, padx=30)
        f.pack(fill="x", pady=14)

        self.entry = criar_entry(f, show="*", largura=30)
        self.entry.pack(fill="x", ipady=6)
        self.entry.focus_set()

        btn_f = tk.Frame(self, bg=COR_SUPERFICIE)
        btn_f.pack()
        criar_botao(btn_f, "Confirmar", self._ok, padx=16, pady=5).pack(side="left", padx=6)
        criar_botao(btn_f, "Cancelar", self._cancelar,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._ok())

    def _ok(self):       self.result = self.entry.get(); self.destroy()
    def _cancelar(self): self.result = None;             self.destroy()


class AddPasswordDialog(tk.Toplevel):
    """Adicionar nova credencial ao cofre."""
    def __init__(self, parent, user_id, master_pw):
        super().__init__(parent)
        self.title("Nova Credencial")
        self.configure(bg=COR_SUPERFICIE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.user_id   = user_id
        self.master_pw = master_pw

        _centrar(self, parent, 480, 420)

        # Título
        tk.Label(self, text="➕  Nova Credencial", font=("Segoe UI", 13, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(pady=(24, 4), anchor="w", padx=30)
        tk.Frame(self, bg=COR_BORDA, height=1).pack(fill="x", padx=30, pady=(0, 16))

        f = tk.Frame(self, bg=COR_SUPERFICIE, padx=30)
        f.pack(fill="x")

        def campo(lbl, attr, show=None):
            tk.Label(f, text=lbl, font=("Segoe UI", 9, "bold"),
                     bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x", pady=(8, 2))
            e = criar_entry(f, show=show, largura=40)
            e.pack(fill="x", ipady=5)
            setattr(self, attr, e)

        campo("Serviço *",          "entry_service")
        campo("Utilizador / email", "entry_username")
        campo("Password (vazia = gerar automaticamente)", "entry_password")

        # Opções
        opts = tk.Frame(f, bg=COR_SUPERFICIE)
        opts.pack(fill="x", pady=(12, 0))

        self.gerada_var   = tk.BooleanVar()
        self.honeypot_var = tk.BooleanVar()
        self.panico_var   = tk.BooleanVar()

        def chk(parent, texto, var, cmd=None):
            cb = tk.Checkbutton(parent, text=texto, variable=var,
                                bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM,
                                selectcolor=COR_CARD, activebackground=COR_SUPERFICIE,
                                font=FONTE_LABEL, bd=0, highlightthickness=0,
                                command=cmd)
            cb.pack(anchor="w", pady=2)
            return cb

        chk(opts, "Gerar password automaticamente",      self.gerada_var,   self._toggle_pw)
        chk(opts, "⚠️  Marcar como isco (honeypot)",     self.honeypot_var)
        chk(opts, "👁  Mostrar no cofre falso (pânico)", self.panico_var)

        # Botões
        tk.Frame(self, bg=COR_BORDA, height=1).pack(fill="x", padx=30, pady=(16, 0))
        btn_f = tk.Frame(self, bg=COR_SUPERFICIE, pady=14)
        btn_f.pack()

        criar_botao(btn_f, "💾  Guardar", self._guardar, padx=16, pady=5).pack(side="left", padx=6)
        criar_botao(btn_f, "Cancelar", self.destroy,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=6)

    def _toggle_pw(self):
        state = "disabled" if self.gerada_var.get() else "normal"
        self.entry_password.config(state=state)

    def _guardar(self):
        service = self.entry_service.get().strip()
        if not service:
            messagebox.showerror("Erro", "Serviço é obrigatório.", parent=self); return

        username = self.entry_username.get().strip() or None
        plain_pw = None
        if not self.gerada_var.get():
            plain_pw = self.entry_password.get().strip()
            if not plain_pw:
                messagebox.showerror("Erro", "Introduz uma password ou marca 'Gerar automaticamente'.", parent=self)
                return

        vault.add_password(self.user_id, self.master_pw, service, username,
                           plain_pw, self.honeypot_var.get(), self.panico_var.get())
        messagebox.showinfo("Guardado", "Credencial guardada com sucesso!", parent=self)
        self.destroy()


class AddFakePasswordDialog(tk.Toplevel):
    """Adicionar entrada ao cofre falso (modo pânico)."""
    def __init__(self, parent, user_id):
        super().__init__(parent)
        self.title("Adicionar ao Cofre Falso")
        self.configure(bg=COR_SUPERFICIE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.user_id = user_id
        self.result  = False

        _centrar(self, parent, 420, 280)

        tk.Label(self, text="Cofre Falso — Nova Entrada", font=("Segoe UI", 12, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_AVISO).pack(pady=(24, 4))
        tk.Frame(self, bg=COR_BORDA, height=1).pack(fill="x", padx=30, pady=(0, 16))

        f = tk.Frame(self, bg=COR_SUPERFICIE, padx=30)
        f.pack(fill="x")

        def campo(lbl, attr, show=None):
            tk.Label(f, text=lbl, font=("Segoe UI", 9, "bold"),
                     bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, anchor="w").pack(fill="x", pady=(8, 2))
            e = criar_entry(f, show=show, largura=38)
            e.pack(fill="x", ipady=5)
            setattr(self, attr, e)

        campo("Serviço *",          "entry_service")
        campo("Utilizador / email", "entry_username")
        campo("Password (opcional)", "entry_password")

        self.gerar_var = tk.BooleanVar()
        tk.Checkbutton(f, text="Gerar automaticamente", variable=self.gerar_var,
                       bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM, selectcolor=COR_CARD,
                       activebackground=COR_SUPERFICIE, font=FONTE_LABEL, bd=0,
                       highlightthickness=0, command=self._toggle
                       ).pack(anchor="w", pady=(8, 0))

        btn_f = tk.Frame(self, bg=COR_SUPERFICIE, pady=16)
        btn_f.pack()
        criar_botao(btn_f, "Guardar", self._guardar, padx=16, pady=5).pack(side="left", padx=6)
        criar_botao(btn_f, "Cancelar", self.destroy,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=6)

    def _toggle(self):
        self.entry_password.config(state="disabled" if self.gerar_var.get() else "normal")

    def _guardar(self):
        service = self.entry_service.get().strip()
        if not service:
            messagebox.showerror("Erro", "Serviço é obrigatório.", parent=self); return
        username = self.entry_username.get().strip() or None
        password = "••••••••" if self.gerar_var.get() else (self.entry_password.get().strip() or "••••••••")
        vault.add_fake_password(self.user_id, service, username, password)
        self.result = True
        self.destroy()


class ConfirmDialog(tk.Toplevel):
    def __init__(self, parent, mensagem):
        super().__init__(parent)
        self.title("Confirmação")
        self.configure(bg=COR_SUPERFICIE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = False

        _centrar(self, parent, 400, 180)

        tk.Label(self, text=mensagem, font=FONTE_PADRAO, bg=COR_SUPERFICIE,
                 fg=COR_TEXTO, wraplength=340, justify="center").pack(pady=28, padx=24)

        btn_f = tk.Frame(self, bg=COR_SUPERFICIE)
        btn_f.pack()

        criar_botao(btn_f, "Sim", self._sim,
                    cor=COR_SUCESSO, cor_hover=COR_SUCESSO_HV, padx=20, pady=5
                    ).pack(side="left", padx=8)
        criar_botao(btn_f, "Não", self._nao,
                    cor=COR_ERRO, cor_hover=COR_ERRO_HV, padx=20, pady=5
                    ).pack(side="left", padx=8)

        # Foco no "Não" para evitar confirmação acidental
        self.after(50, lambda: self.focus_set())

    def _sim(self): self.result = True;  self.destroy()
    def _nao(self): self.result = False; self.destroy()
