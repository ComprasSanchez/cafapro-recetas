import tkinter as tk

class Header(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#E6E6E6", height=28)
        self.pack_propagate(False)

        # ESTRUCTURA REAL DEL MENÚ
        menus = {
            "Auditoría": [
                "Lotes Temporales",
            ],
        }

        for menu_name, opciones in menus.items():

            # Crear menú desplegable
            mb = tk.Menubutton(
                self,
                text=menu_name,
                bg="#E6E6E6",
                fg="black",
                activebackground="#D0D0D0",
                activeforeground="black",
                relief="flat",
                padx=10,
                font=("Segoe UI", 9)
            )

            menu = tk.Menu(
                mb,
                tearoff=0,
                bg="white",
                fg="black",
                activebackground="#D0D0D0",
                font=("Segoe UI", 9)
            )

            # Agregar todas las opciones dinámicamente
            for opcion in opciones:
                if opcion == "Salir":
                    menu.add_separator()
                    menu.add_command(label="Salir")
                else:
                    menu.add_command(label=opcion)

            mb.config(menu=menu)
            mb.pack(side="left")

