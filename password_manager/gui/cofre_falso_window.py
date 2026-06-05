"""
Ecrã do Cofre Falso (Modo Pânico) - IronVault.
Aparência idêntica ao cofre real para não levantar suspeitas.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import threading, time, pyperclip

from gui.styles import *
from core import vault


class CofreFalsoFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller     = controller
        self.user_id        = None
        self.username       = None
        self.fake_vault_data = []
        self._criar_widgets()

    def set_user_data(self, user_id, username):
        self.user_id  = user_id
        self.username = username
        self.lbl_user.config(text=f"👤  {username}")
        self._carregar()

    # ── LAYOUT ───────────────────────────────────────────────────

    def _criar_widgets(self):
        # Header — idêntico ao cofre real (não levantar suspeitas)
        header = tk.Frame(self, bg=COR_SUPERFICIE, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🔐  IronVault", font=("Segoe UI", 14, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(side="left", padx=20, pady=16)

        right = tk.Frame(header, bg=COR_SUPERFICIE)
        right.pack(side="right", padx=16, fill="y")

        self.lbl_user = tk.Label(right, text="", font=("Segoe UI", 9),
                                  bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM)
        self.lbl_user.pack(side="left", pady=20, padx=(0, 12))

        criar_botao(right, "Sair", self._sair,
                    cor=COR_ERRO, cor_hover=COR_ERRO_HV, padx=14, pady=5
                    ).pack(side="left", pady=14)

        # Barra de acções — igual ao cofre real
        toolbar = tk.Frame(self, bg=COR_CARD, pady=8)
        toolbar.pack(fill="x")

        acoes = [
            ("➕  Adicionar",   COR_PRINCIPAL, COR_PRINCIPAL_HV, self._adicionar),
            ("🔑  Gerar",        COR_DESTAQUE,  "#0891b2",         self._gerar),
            ("✅  Check-in",     COR_SUCESSO,   COR_SUCESSO_HV,    self._checkin),
            ("🚨  Pânico",       COR_AVISO,     COR_AVISO_HV,      self._panico_ativo),
            ("👥  Guardiões",    COR_SECUNDARIA, COR_BORDA,        self._guardioes),
        ]
        for texto, cor, hv, cmd in acoes:
            criar_botao(toolbar, texto, cmd, cor=cor, cor_hover=hv,
                        padx=14, pady=5).pack(side="left", padx=(8, 0))

        # Barra de pesquisa
        search_bar = tk.Frame(self, bg=COR_FUNDO, pady=12)
        search_bar.pack(fill="x", padx=20)

        tk.Label(search_bar, text="🔍", bg=COR_FUNDO, fg=COR_TEXTO_DIM,
                 font=("Segoe UI", 11)).pack(side="left", padx=(0, 6))

        self.entry_search = criar_entry(search_bar, largura=40)
        self.entry_search.pack(side="left", ipady=5, fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self._filtrar)

        # Tabela
        tree_frame = tk.Frame(self, bg=COR_FUNDO)
        tree_frame.pack(fill="both", expand=True, padx=20)

        cols = ("servico", "username", "tipo")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Custom.Treeview", selectmode="browse")

        self.tree.heading("servico",  text="Serviço",    anchor="w")
        self.tree.heading("username", text="Utilizador", anchor="w")
        self.tree.heading("tipo",     text="Tipo",       anchor="w")

        self.tree.column("servico",  width=240, anchor="w")
        self.tree.column("username", width=240, anchor="w")
        self.tree.column("tipo",     width=100, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                           command=self.tree.yview, style="Custom.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Barra inferior
        bottom = tk.Frame(self, bg=COR_SUPERFICIE, pady=10)
        bottom.pack(fill="x")

        criar_botao(bottom, "👁  Ver Password",  self._ver,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=12)
        criar_botao(bottom, "📋  Copiar",        self._copiar,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left")
        criar_botao(bottom, "🗑  Apagar",         self._apagar,
                    cor=COR_ERRO, cor_hover=COR_ERRO_HV, padx=16, pady=5
                    ).pack(side="right", padx=12)

        self.lbl_status = tk.Label(bottom, text="", font=("Segoe UI", 9),
                                    bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM)
        self.lbl_status.pack(side="right", padx=12)

    # ── DADOS ────────────────────────────────────────────────────

    def _carregar(self):
        self.fake_vault_data = vault.get_fake_vault(self.user_id)
        self._atualizar_tree()

    def _atualizar_tree(self, dados=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        lista = dados if dados is not None else self.fake_vault_data
        for p in lista:
            self.tree.insert("", "end", iid=p["id"],
                              values=(p["service"], p["username"] or "—", "Normal"))
        n = len(lista)
        self.lbl_status.config(text=f"{n} entrada{'s' if n != 1 else ''}")

    def _filtrar(self, event=None):
        q = self.entry_search.get().strip().lower()
        filtrado = [p for p in self.fake_vault_data
                    if q in p["service"].lower() or q in (p["username"] or "").lower()]
        self._atualizar_tree(filtrado)

    def _selecao(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleciona uma entrada primeiro.")
            return None
        return next((p for p in self.fake_vault_data if p["id"] == int(sel[0])), None)

    # ── ACÇÕES ───────────────────────────────────────────────────

    def _ver(self):
        pw = self._selecao()
        if not pw: return
        win = tk.Toplevel(self)
        win.title("Password")
        win.configure(bg=COR_SUPERFICIE)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("380x180")
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - 380) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 180) // 2
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=pw["service"], font=("Segoe UI", 11, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(pady=(20, 8))
        pw_frame = tk.Frame(win, bg=COR_CARD, padx=16, pady=10)
        pw_frame.pack(fill="x", padx=24)
        tk.Label(pw_frame, text=pw["password"], font=FONTE_MONO,
                 bg=COR_CARD, fg=COR_DESTAQUE).pack()
        criar_botao(win, "Fechar", win.destroy,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(pady=14)

    def _copiar(self):
        pw = self._selecao()
        if not pw: return
        pyperclip.copy(pw["password"])
        messagebox.showinfo("Copiado", "Password copiada! Será limpa em 30 segundos.")
        threading.Thread(target=self._limpar_clipboard, daemon=True).start()

    def _limpar_clipboard(self):
        time.sleep(30)
        pyperclip.copy("")

    def _adicionar(self):
        from gui.dialogs import AddFakePasswordDialog
        dlg = AddFakePasswordDialog(self, self.user_id)
        self.wait_window(dlg)
        if dlg.result:
            self._carregar()

    def _gerar(self):
        pw = vault.generate_password()
        pyperclip.copy(pw)
        messagebox.showinfo("Gerador", f"Password gerada e copiada:\n{pw}")
        threading.Thread(target=self._limpar_clipboard, daemon=True).start()

    def _apagar(self):
        pw = self._selecao()
        if not pw: return
        if messagebox.askyesno("Confirmar", f"Apagar '{pw['service']}'?"):
            if vault.delete_fake_password(self.user_id, pw["id"]):
                self._carregar()
                messagebox.showinfo("Apagado", "Entrada removida.")
            else:
                messagebox.showerror("Erro", "Não foi possível apagar.")

    # Botões de simulação (credíveis para o atacante)
    def _checkin(self):
        messagebox.showinfo("Check-in", "✅ Check-in realizado com sucesso.")

    def _panico_ativo(self):
        messagebox.showinfo("Modo Pânico", "O Modo Pânico já está ativo.")

    def _guardioes(self):
        messagebox.showinfo("Guardiões", "Configuração de guardiões indisponível neste modo.")

    def _sair(self):
        self.controller.logout()
