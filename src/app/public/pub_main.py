from __future__ import absolute_import, print_function

from ..tkimport import Tk
from .pub_canvas import SharedCanvas
from .pub_code_box import CodeBox
from .pub_peers import PeerBox

class SharedSpace(Tk.Frame):
    def __init__(self, parent):
        # Create a single frame to hold the representations of code chunks
        self.parent = parent
        Tk.Frame.__init__(self, self.parent.root)

        # Canvas and y-scroll
        self.canvas = SharedCanvas(self, width=640, height=480, bg="gray")

        self.y_scroll = Tk.Scrollbar(self)
        self.y_scroll.config(command=self.canvas.yview, orient=Tk.VERTICAL)

        self.canvas.config(
            yscrollcommand=self.y_scroll.set,
            scrollregion=self.canvas.bbox(Tk.ALL)
            )

        # Box for changing size - self.parent.root

        self.drag = Tk.Frame( self, bg="white", width=5, cursor="sb_h_double_arrow") # why does it need to be parent.root?
        self.drag.bind("<Button-1>",        self.drag_mouseclick)        
        self.drag.bind("<ButtonRelease-1>", self.drag_mouserelease)
        self.drag.bind("<B1-Motion>",       self.drag_mousedrag)

        self.drag_mouse_down = False

        # Peers list

        self.peer_box = PeerBox(self)

        # Only expand canvas

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Grid
        
        self.canvas.grid(row=0, column=0, sticky=Tk.NSEW)
        self.drag.grid(row=0, column=1, sticky=Tk.NSEW)
        self.peer_box.grid(row=0, column=2, sticky=Tk.NSEW)
        self.peer_box.grid_propagate(False)
        self.y_scroll.grid(row=0, column=3, sticky=Tk.NSEW)

        # Codelet / codebox information

        self.codelets = {}

    def add_codelet(self, codelet):
        """ Adds a new codelet to the canvas wrapped in a CodeBox instance """
        self.codelets[codelet.id] = CodeBox(self, codelet)
        return

    def redraw(self):
        self.canvas.redraw()

    def drag_mouseclick(self, event=None):
        """ Flags the mouse as clicked for drag action """
        self.drag_mouse_down = True
        self.grid_propagate(False)
        return

    def drag_mouserelease(self, event=None):
        """ Flags the mouse has been released and gives focus to the app.text if it exists """
        self.drag_mouse_down = False
        
        if self.parent.text is not None:
        
            self.parent.text.focus_set()
        
        return

    def drag_mousedrag(self, event=None):
        """ Resizes the canvas and listbox """

        if self.drag_mouse_down:

            delta = (self.drag.winfo_rootx() - event.x_root)

            self.peer_box.config(width=self.peer_box.winfo_width() + delta)
            self.canvas.config(width=self.canvas.winfo_width() - delta)

            return "break"

        return