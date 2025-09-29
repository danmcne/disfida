# main.py
import tkinter as tk
from card_game_gui import CardGameGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = CardGameGUI(root)
    root.mainloop()
