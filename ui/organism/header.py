import tkinter as tk

class Header(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#E6E6E6", height=28)
        self.pack_propagate(False)

        # Lista de menús a mostrar
        menus = [
            "Sistema", "Archivo", "Recepción", "Presentaciones", "Compras",
            "Ventas", "Caja y bancos", "Contabilidad", "Auditoría", "Varios", "Ayuda"
        ]

        for menu_name in menus:
            # Crear Menubutton
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

            # Crear el menú asociado
            menu = tk.Menu(
                mb,
                tearoff=0,
                bg="white",
                fg="black",
                activebackground="#D0D0D0",
                font=("Segoe UI", 9)
            )

            # Agregar items ficticios (para que los veas funcionar)
            menu.add_command(label=f"{menu_name} - Opción 1")
            menu.add_command(label=f"{menu_name} - Opción 2")
            menu.add_separator()
            menu.add_command(label=f"{menu_name} - Salir")

            # Asociar el menú al Menubutton
            mb.config(menu=menu)

            # Agregar al header
            mb.pack(side="left")
