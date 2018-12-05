from __future__ import absolute_import, print_function

from ...utils import GET_USER_COLOUR
from ..tkimport import Tk

class PeerBox(Tk.Frame):
    def __init__(self, parent, *args, **kwargs):

        self.parent = parent # Is the "SharedSpace"
        self.app    = parent.parent # is the whole app
    
        Tk.Frame.__init__(self, self.parent, width=250)

        # self.listbox = Tk.Listbox(self, bg="White", font=self.parent.parent.font, width=20)

        self.listbox = Tk.Canvas(self, bg="White", width=20)
        
        self.listbox.grid(row=0, column=0, sticky=Tk.NSEW)

        self.listbox.bind("<Button-1>", lambda e: "break")
        self.listbox.bind("<B1-Motion>", lambda e: "break")

        self.rowconfigure(0, weight=1) # Expand
        self.columnconfigure(0, weight=1)

        # Use app font

        self.padx = 2
        self.pady = 2

        self.box_height = 0

        self.font = self.app.font

        self.colours = ["#565656", "#7f7f7f", "#7f7f7f"]

        # Counter for dots drawing

        self.ticker = 0

        self.refresh(internal_call=True)

    def refresh(self, internal_call=False):
        """ Clears the user list and redraws  """
        
        # Clear the contents
        
        self.listbox.delete("all")

        i = 0

        for user_id, user in self.app.users.items():

            y_pos = i * self.box_height

            self.draw_user_box(y_pos, user)

            i += 1

        # Increase counter

        self.ticker = (self.ticker + 1) % 3

        # Recursive call if we don't call from external (stops extra recursive calls)

        if internal_call:

            self.after(500, lambda: self.refresh(internal_call=True))

        return 

    def draw_user_box(self, y_pos, user):
        # Draw text
        text = self.listbox.create_text(self.padx, y_pos + self.pady, 
                    anchor=Tk.NW, 
                    text=user.get_name(),
                    width=self.get_width() - (self.padx * 2), 
                    font=self.font
                    )
        
        # Get bbox of font
        bounds = self.listbox.bbox(text) 
        
        # Draw background
        bbox = [bounds[0] - self.padx, bounds[1] - self.pady, self.get_width(), bounds[3] + self.pady]

        rect = self.listbox.create_rectangle( bbox, fill=user.get_colour() )
        
        # Draw dots

        dots = self.draw_dots(y_pos)

        # Organise z-axis

        self.listbox.tag_lower(rect, text)

        # if user.get_is_typing():
        if True:

            self.listbox.tag_lower(text)
            self.listbox.tag_lower(rect)

        else:

            for dot in dots:

                self.listbox.tag_lower(dot)

        # Store height
        
        self.box_height = bounds[3] - bounds[1]
        
        return 

    def draw_dots(self, y_pos):
        """ Draws 3 circles and returns a list of their ID's """
        dots = []
        total_width = self.get_width()
        shade = self.get_colours()

        # Draw the circles in the 5/6th of the 

        x_pos = total_width * 2 / 3
        
        for n in range(3):
        
            w = h = int(self.box_height / 4)
            
            x = x_pos + (w * n * 1.5)
            y = int(y_pos + ((self.box_height * 2 / 3) - (h / 2)))

            n = self.listbox.create_oval([x, y, x + w, y + h], fill=shade[n], outline=shade[n])
            
            dots.append(n)
        
        return dots

    def get_colours(self):
        return self.colours[-self.ticker:] + self.colours[:-self.ticker]

    def get_width(self):
        return self.listbox.winfo_width()
