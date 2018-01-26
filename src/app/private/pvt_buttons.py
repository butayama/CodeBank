from ..tkimport import Tk

class CommandButtons(Tk.Frame):
    """docstring for TextInput"""
    def __init__(self, parent, commands):
        
        Tk.Frame.__init__(self, parent)
        self.config(width=5, height=25)

        self.num_buttons = 0

        self.names    = ["PUSH", "SOLO", "RESET"]
        self.commands = { name: commands[name] for name in self.names }

        self.button = {}

        for i, name in enumerate(self.names):

            self.button[name] = Tk.Button(self, text=name, relief=Tk.RAISED, borderwidth=1, command=self.commands[name]) # Maybe use a label
            self.button[name].grid(row=0, column=self.num_buttons, padx=4)
            self.num_buttons += 1