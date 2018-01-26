from .main import *
from .connection_input import popup_window
from ..utils import get_players

# Class for interface for client-side

class App(BasicApp):
    def __init__(self, *args, **kwargs):
        
        BasicApp.__init__(self, *args, **kwargs)

        self.root.title("CodeBank Client: Not Connected")
        self.root.state("zoomed")

        # Menu bar

        self.menu = MenuBar(self)
        self.root.config(menu=self.menu)

        # Lower text box for client text entry

        self.workspace = Workspace(self)
        self.workspace.grid(row=2, column=0, sticky=Tk.NSEW, columnspan=2)

        # Data handlers to handle messages from the server

        self.handlers = {
            HANDLE_KILL    : self.kill,
            HANDLE_UPDATE  : self.recv_codelet,
            HANDLE_DELETE  : self.delete_codelet,
            HANDLE_LOAD    : self.load_codelet,
            HANDLE_DISABLE : self.disable_codelet,
            HANDLE_UNDO    : self.rollback,
            HANDLE_NAME    : self.add_user,
            HANDLE_SET_ID  : self.set_user_id,
            HANDLE_RELEASE : self.release_codelet,
            HANDLE_ERROR   : self.raise_error,
            HANDLE_INFO    : self.print_msg,
            HANDLE_REMOVE  : self.remove_user,
            HANDLE_HISTORY : self.load_codelet_history,
        }

        # This stores the codelet being currently edited

        self.current_codelet  = -1
        self.codelet_on_click = self.request_codelet

        # Booleans

        self.solo_on = False

        # Don't allow users to use buttons / text box until connected

        self.disable()

    def get_connection_info(self):
        """ Open dialog for a user to enter their connection information """
        
        self.popup = popup_window(self.root, title="Connect to server")
        self.popup.host.focus_set()

        # Put the popup on top
        
        self.root.wait_window(self.popup.top)

        return self.popup.value

    def init_connection(self, event=None):
        """ Create an input dialog for entering information about the user and server """
        if not self.socket.is_connected():
            
            info = self.get_connection_info()

            if info is not None:

                try:
                
                    self.socket.connect(*info)
                    
                    self.workspace.set_connection(self.socket)

                    self.connected = True

                    self.workspace.text.focus_set()

                except ConnectionError as e:

                    print("Connection Error: {}".format(e))
        return

    def disable(self):
        """ Stop textbox and buttons from being used """
        self._is_enabled = False
        self.workspace.text.config(state=Tk.DISABLED, bg="#b3b3b3")
        return

    def enable(self):
        """ Allows textbox and buttons being used """
        self._is_enabled = True
        self.workspace.text.config(state=Tk.NORMAL, bg="White")
        return

    def clear(self):
        """ Clears the text box and resets the codelet we're working on """
        self.workspace.text.clear()
        # TODO - remove undo stack

        # Send a message to un-edit the code on the server
        if self.get_codelet_id() != -1:
            self.socket.send( MESSAGE_RELEASE(self.get_user_id(), self.get_codelet_id()) )
        self.set_codelet_id(-1)
        return

    # Server communications

    def get_codelet_id(self):
        """ Returns the ID of the currently edited codelet"""
        return self.current_codelet

    def get_user_id(self):
        """ Returns the local user's id """
        return self.socket.user_id

    def set_codelet_id(self, c_id):
        self.current_codelet = c_id
        return

    def request_codelet(self, codelet_id):
        """ Triggered by clicking on a codebox. Sends a message to the server to request edit
            permissions for that codelet """
        if self.get_codelet_id() == -1:

            self.socket.send(MESSAGE_REQUEST(self.get_user_id(), codelet_id))

        return

    def release_codelet(self, user_id, codelet_id):
        """ Un-locks a codelet to be re-edited with no changes """
        self.sharedspace.codelets[codelet_id].unassign_editor()
        self.sharedspace.redraw()
        return

    def push_code_to_remote(self, event=None):
        """ Triggered by PUSH button - pushes code to the remote (and also pulls from) and resets the text box """

        if self._is_enabled:
        
            # Get code contents and package together with information which, if any, codelet is being sent

            if self.solo_on:

                self.solo_local_code()

            code = self.workspace.text.get_text()

            if len(code.strip()) > 0:

                data = MESSAGE_PUSH(self.get_user_id(), self.get_codelet_id(), code)

                if self.socket.is_connected():

                    self.socket.send(data)

                # Clear text and reset

                self.clear()

        return 

    def solo_local_code(self, event=None):
        """ Will mute other players currently being run using FoxDot Player.solo method.
            Triggered by the SOLO button. """
        if self._is_enabled:
            players = get_players(self.workspace.text.get_text())
            if len(players):
                self.solo_on = not self.solo_on
                if len(players) > 1:
                    cmd = "Group({}).solo({})".format(", ".join(players), int(self.solo_on))
                elif len(players) == 1:
                    cmd = "{}.solo({})".format(players[0], int(self.solo_on))
                self.evaluate(cmd)
        return

    def reset_program_state(self, event=None):
        """ Resets the program state to before the last push, triggered by the RESET button """

        if self._is_enabled:

            if self.solo_on:

                self.solo_local_code()

            code = self.workspace.text.get_text()

            players = get_players(code)

            for player in players:

                self.evaluate("{}.reset()".format(player))

            # e.g. r1.reset() then eval the history of the codelet?

            codelet_id = self.get_codelet_id()

            if codelet_id != -1:

                codelet = self.sharedspace.codelets[codelet_id].get_codelet()

                self.evaluate_codelet_history(codelet)

            self.clear() # sends data to server

        return

    def my_id(self, user_id):
        """ Returns True if the  user id is that of the local client """
        return user_id == self.socket.user_id

    # Handler methods

    def load_codelet(self, user_id, codelet_id):
        """ Handles a codelet coming in to be edited """
        # If the user id is the local user, load it
        if self.my_id(user_id):

            self.workspace.load_from_codelet(codelet_id)
        
        # Flag it to be grey and redraw
        
        self.sharedspace.codelets[codelet_id].assign_editor(user_id)
        
        self.sharedspace.redraw()

        return

    def load_codelet_history(self, user_id, codelet_id, data, order_id ):
        """ Only called when connecting to a server: creates codelets and loads the history. """

        user_id, string = data[0]

        codelet = Codelet(codelet_id, user_id, string)

        codelet.load_history(data)

        self.sharedspace.add_codelet(codelet)

        # Evaluate the code

        self.evaluate_codelet_history(codelet)

        return

    def disable_codelet(self, user_id, codelet_id):
        """ Flags a codelet to be disabled i.e. cannot be loaded """
        return

    def recv_codelet(self, user_id, code_id, string, order_id):
        """ Handles a new/updated codelet """

        # Find the code_id

        codelet = self.sharedspace.codelets.get(code_id, None)

        if codelet is not None:

            codelet.update(user_id, string, order_id)

        else:

            codelet = Codelet(code_id, user_id, string)

            self.sharedspace.add_codelet(codelet)

        # Evaluate the code

        self.evaluate(codelet.get_text())

        return

    def delete_codelet(self, user_id, data):
        return

    def rollback(self, user_id, data):
        return


    def add_user(self, user_id, name):
        """ Adds a user to the address book and updates the UI title if the local client """

        BasicApp.add_user(self, user_id, name)
        
        # Update the UI
        
        if self.my_id(user_id):
        
            self.root.title("CodeBank Client. Logged in as {}".format(name))

        return

    def set_user_id(self, user_id):
        self.socket.user_id = user_id
        return

    def raise_error(self, user_id, err_msg):
        """ Raises a ConnectionError that displays err_msg (string) in the console.
            Triggered by HANDLE_ERROR message. """
        raise ConnectionError(err_msg)

    def print_msg(self, user_id, string):
        """ Prints string to the console. Triggered by HANDLE_INFO message. """
        return print(string)