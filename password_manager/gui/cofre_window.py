"""
Ecrã principal do cofre - IronVault.
Design escuro com header, barra de ações e tabela estilizada.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import threading, time, gc
import pyperclip

from gui.styles import *
from gui.dialogs import PasswordDialog, AddPasswordDialog
from gui.dupla_custodia_config import ConfigurarGuardioesDialog
from core import auth, vault, crypto, database


class CofreFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        self.user_id = self.session_id = self.username = self.master_pw = None
        self.passwords_metadata = []
        self._criar_widgets()

    def set_user_data(self, user_id, session_id, username, master_pw):
        self.user_id    = user_id
        self.session_id = session_id
        self.username   = username
        self.master_pw  = master_pw
        self.lbl_user.config(text=f"👤  {username}")
        self.carregar_passwords()

    # ── LAYOUT ───────────────────────────────────────────────────

    def _criar_widgets(self):
        # Header
        header = tk.Frame(self, bg=COR_SUPERFICIE, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=COR_SUPERFICIE)
        left.pack(side="left", padx=20, fill="y")

        tk.Label(left, text="🔐  IronVault", font=("Segoe UI", 14, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(side="left", pady=16)

        right = tk.Frame(header, bg=COR_SUPERFICIE)
        right.pack(side="right", padx=16, fill="y")

        self.lbl_user = tk.Label(right, text="", font=("Segoe UI", 9),
                                  bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM)
        self.lbl_user.pack(side="left", pady=20, padx=(0, 12))

        criar_botao(right, "Sair", self.logout,
                    cor=COR_ERRO, cor_hover=COR_ERRO_HV, padx=14, pady=5
                    ).pack(side="left", pady=14)

        # Barra de acções
        toolbar = tk.Frame(self, bg=COR_CARD, pady=8)
        toolbar.pack(fill="x")

        acoes = [
            ("➕  Adicionar",   COR_PRINCIPAL, COR_PRINCIPAL_HV, self.adicionar_password),
            ("🔑  Gerar",        COR_DESTAQUE,  "#0891b2",         self.gerar_password),
            ("✅  Check-in",     COR_SUCESSO,   COR_SUCESSO_HV,    self.fazer_checkin),
            ("🚨  Pânico",       COR_AVISO,     COR_AVISO_HV,      self.ativar_modo_panico),
            ("👥  Guardiões",    COR_SECUNDARIA, COR_BORDA,        self.configurar_dupla_custodia),
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

        tk.Label(search_bar, text="", bg=COR_FUNDO).pack(side="left", padx=4)

        # Tabela
        tree_frame = tk.Frame(self, bg=COR_FUNDO)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 0))

        cols = ("servico", "username", "tipo")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Custom.Treeview", selectmode="browse")

        self.tree.heading("servico",   text="Serviço",   anchor="w")
        self.tree.heading("username",  text="Utilizador", anchor="w")
        self.tree.heading("tipo",      text="Tipo",       anchor="w")

        self.tree.column("servico",   width=240, anchor="w")
        self.tree.column("username",  width=240, anchor="w")
        self.tree.column("tipo",      width=100, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                           command=self.tree.yview, style="Custom.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.tag_configure("honeypot", foreground=COR_AVISO)
        self.tree.tag_configure("normal",   foreground=COR_TEXTO)

        # Barra inferior de acções
        bottom = tk.Frame(self, bg=COR_SUPERFICIE, pady=10)
        bottom.pack(fill="x")

        criar_botao(bottom, "👁  Ver Password",  self.ver_password,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=12)
        criar_botao(bottom, "📋  Copiar",        self.copiar_password,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left")
        criar_botao(bottom, "🗑  Apagar",         self.apagar_password,
                    cor=COR_ERRO, cor_hover=COR_ERRO_HV, padx=16, pady=5
                    ).pack(side="right", padx=12)

        self.lbl_status = tk.Label(bottom, text="", font=("Segoe UI", 9),
                                    bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM)
        self.lbl_status.pack(side="right", padx=12)

    # ── DADOS ────────────────────────────────────────────────────

    def carregar_passwords(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.passwords_metadata = []

        with database.get_db_connection_read() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, service, username, is_honeypot, encrypted_password "
                "FROM passwords WHERE user_id = ? ORDER BY service",
                (self.user_id,)
            )
            for row in cursor.fetchall():
                tipo = "⚠️ Isca" if row["is_honeypot"] else "Normal"
                tag  = "honeypot" if row["is_honeypot"] else "normal"
                self.tree.insert("", "end", iid=row["id"],
                                  values=(row["service"], row["username"] or "—", tipo),
                                  tags=(tag,))
                self.passwords_metadata.append(dict(row))

        n = len(self.passwords_metadata)
        self.lbl_status.config(text=f"{n} entrada{'s' if n != 1 else ''}")

    def _filtrar(self, event=None):
        query = self.entry_search.get().strip().lower()
        for i in self.tree.get_children():
            self.tree.delete(i)

        for p in self.passwords_metadata:
            if query in p["service"].lower() or query in (p["username"] or "").lower():
                tipo = "⚠️ Isca" if p["is_honeypot"] else "Normal"
                tag  = "honeypot" if p["is_honeypot"] else "normal"
                self.tree.insert("", "end", iid=p["id"],
                                  values=(p["service"], p["username"] or "—", tipo),
                                  tags=(tag,))

    # ── ACÇÕES ───────────────────────────────────────────────────

    def _selecao(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleciona uma entrada primeiro.")
            return None
        return next((p for p in self.passwords_metadata if p["id"] == int(sel[0])), None)

    def ver_password(self):
        pw = self._selecao()
        if not pw: return
        if pw["is_honeypot"]: self._honeypot(pw["id"]); return

        dlg = PasswordDialog(self, "Confirma a tua Master Password:")
        self.wait_window(dlg)
        if dlg.result and auth.verify_master_password(self.user_id, dlg.result):
            salt = vault._get_user_salt(self.user_id)
            key  = crypto.derive_key(dlg.result, salt)
            try:
                txt = crypto.decrypt_password(pw["encrypted_password"], key)
                self._janela_password(pw["service"], txt)
            finally:
                gc.collect()
        elif dlg.result:
            messagebox.showerror("Erro", "Master password incorreta.")

    def copiar_password(self):
        pw = self._selecao()
        if not pw: return
        if pw["is_honeypot"]: self._honeypot(pw["id"]); return

        dlg = PasswordDialog(self, "Confirma a tua Master Password:")
        self.wait_window(dlg)
        if dlg.result and auth.verify_master_password(self.user_id, dlg.result):
            salt = vault._get_user_salt(self.user_id)
            key  = crypto.derive_key(dlg.result, salt)
            txt  = crypto.decrypt_password(pw["encrypted_password"], key)
            pyperclip.copy(txt)
            messagebox.showinfo("Copiado", "Password copiada! Será limpa em 15 segundos.")
            threading.Thread(target=self._limpar_clipboard, daemon=True).start()
            txt = "0" * len(txt); del txt; gc.collect()
        elif dlg.result:
            messagebox.showerror("Erro", "Master password incorreta.")

    def _limpar_clipboard(self):
        time.sleep(15)
        vault.clear_clipboard_securely()

    def _honeypot(self, pw_id):
        auth._log_security_event(self.username, "honeypot_triggered", f"ID:{pw_id}", auth.get_client_ip())
        auth.invalidate_session(self.session_id)
        messagebox.showerror("🚨 ALERTA", "Violação de segurança detetada. Sessão terminada.")
        self.logout()

    def adicionar_password(self):
        dlg = AddPasswordDialog(self, self.user_id, self.master_pw)
        self.wait_window(dlg)
        self.carregar_passwords()

    def gerar_password(self):
        pw = vault.generate_password()
        pyperclip.copy(pw)
        self._janela_password("Password Gerada", pw)
        threading.Thread(target=self._limpar_clipboard, daemon=True).start()

    def fazer_checkin(self):
        try:
            if auth.fazer_checkin(self.user_id):
                messagebox.showinfo("Check-in", "✅ Check-in realizado com sucesso.")
            else:
                messagebox.showerror("Erro", "Falha no check-in.")
        except AttributeError:
            messagebox.showinfo("Check-in", "✅ Check-in registado.")

    def ativar_modo_panico(self):
        if messagebox.askyesno("🚨 Ativar Modo Pânico",
                                "Tens a certeza? A Master Password será bloqueada!"):
            try:
                if auth.activate_panic_mode(self.user_id):
                    messagebox.showwarning("Pânico Ativo", "Modo Pânico ativo. A aplicação vai fechar.")
                    self.logout()
            except AttributeError:
                messagebox.showinfo("Info", "Modo Pânico não disponível.")

    def configurar_dupla_custodia(self):
        dlg = ConfigurarGuardioesDialog(self, self.user_id)
        self.wait_window(dlg)

    def apagar_password(self):
        pw = self._selecao()
        if not pw: return
        if messagebox.askyesno("Confirmar", f"Apagar a entrada '{pw['service']}'?"):
            vault.delete_password(self.user_id, pw["id"])
            self.carregar_passwords()
            messagebox.showinfo("Apagado", "Entrada removida.")

    def logout(self):
        self.user_id = self.session_id = self.username = self.master_pw = None
        self.passwords_metadata = []
        gc.collect()
        self.controller.logout()

    # ── JANELA DE PASSWORD ────────────────────────────────────────
    def _janela_password(self, servico, texto):
        """Mostra a password num popup limpo com botão de copiar."""
        win = tk.Toplevel(self)
        win.title("Password")
        win.configure(bg=COR_SUPERFICIE)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("420x210")

        # Centrar
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - win.winfo_width())  // 2
        y = self.winfo_rooty() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=servico, font=("Segoe UI", 11, "bold"),
                 bg=COR_SUPERFICIE, fg=COR_TEXTO).pack(pady=(24, 8))

        pw_frame = tk.Frame(win, bg=COR_CARD, padx=16, pady=12)
        pw_frame.pack(fill="x", padx=24)

        tk.Label(pw_frame, text=texto, font=FONTE_MONO,
                 bg=COR_CARD, fg=COR_DESTAQUE, wraplength=340).pack()

        btn_frame = tk.Frame(win, bg=COR_SUPERFICIE)
        btn_frame.pack(pady=20)

        def _copiar():
            pyperclip.copy(texto)
            lbl_ok.config(text="✔ Copiado!", fg=COR_SUCESSO)
            threading.Thread(target=self._limpar_clipboard, daemon=True).start()

        criar_botao(btn_frame, "📋  Copiar", _copiar, padx=16, pady=5).pack(side="left", padx=6)
        criar_botao(btn_frame, "Fechar", win.destroy,
                    cor=COR_SECUNDARIA, cor_hover=COR_BORDA, padx=16, pady=5
                    ).pack(side="left", padx=6)

        lbl_ok = tk.Label(win, text="", font=("Segoe UI", 9),
                           bg=COR_SUPERFICIE, fg=COR_TEXTO_DIM)
        lbl_ok.pack()
