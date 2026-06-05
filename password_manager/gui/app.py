"""
Módulo principal da aplicação gráfica - IronVault.
Gere a janela principal, navegação entre ecrãs e segurança do ambiente.
"""

import sys, os, gc
import tkinter as tk
from PIL import Image, ImageTk

# Prevenção de Binary Planting / Path Hijacking
if '' in sys.path:         sys.path.remove('')
if os.getcwd() in sys.path: sys.path.remove(os.getcwd())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.styles import *
from gui.login_window      import LoginFrame
from gui.register_window   import RegisterFrame
from gui.cofre_window      import CofreFrame
from gui.cofre_falso_window import CofreFalsoFrame
from gui.recuperacao_window import RecuperacaoFrame
from core import auth, database

database.create_tables()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IronVault — Password Manager")
        self.geometry("900x620")
        self.minsize(780, 540)
        self.configure(bg=COR_FUNDO)

        self._configurar_icone()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = tk.Frame(self, bg=COR_FUNDO)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (LoginFrame, RegisterFrame, CofreFrame, CofreFalsoFrame, RecuperacaoFrame):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.mostrar_frame(LoginFrame)

        self.user_id = self.session_id = self.username = None
        self.master_pw = self.chave_backup = None

        # Protocolo de fecho seguro
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _configurar_icone(self):
        try:
            caminho = os.path.join(os.path.dirname(__file__), 'logo.png')
            img = Image.open(caminho)
            self.icon_img = ImageTk.PhotoImage(img)
            self.iconphoto(True, self.icon_img)
        except Exception:
            pass

    def mostrar_frame(self, frame_class):
        self.frames[frame_class].tkraise()
        gc.collect()

    def login_sucesso(self, user_id, session_id, username, master_pw):
        self.user_id    = user_id
        self.session_id = session_id
        self.username   = username
        self.master_pw  = master_pw
        self.frames[CofreFrame].set_user_data(user_id, session_id, username, master_pw)
        self.mostrar_frame(CofreFrame)

    def login_panico(self, user_id, username):
        self.user_id    = user_id
        self.username   = username
        self.session_id = self.master_pw = None
        self.frames[CofreFalsoFrame].set_user_data(user_id, username)
        self.mostrar_frame(CofreFalsoFrame)

    def login_backup(self, user_id, session_id, username, chave_backup):
        self.user_id      = user_id
        self.session_id   = session_id
        self.username     = username
        self.chave_backup = chave_backup
        self.frames[RecuperacaoFrame].set_user_data(user_id, session_id, username, chave_backup)
        self.mostrar_frame(RecuperacaoFrame)

    def logout(self):
        try:
            if self.session_id:
                auth.invalidate_session(self.session_id)
        except Exception:
            pass

        self.user_id = self.session_id = self.username = None

        if self.master_pw:
            self.master_pw = "0" * len(self.master_pw)
            self.master_pw = None
        if self.chave_backup:
            self.chave_backup = "0" * len(self.chave_backup)
            self.chave_backup = None

        self.mostrar_frame(LoginFrame)
        gc.collect()

    def _fechar(self):
        """Encerra a sessão de forma segura antes de fechar a janela."""
        self.logout()
        self.destroy()


def iniciar_gui():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    iniciar_gui()
