# card_image_manager.py
from PIL import Image, ImageTk
import os

class CardImageManager:
    def __init__(self):
        self.card_images = {}
        self.card_images_rotated = {}
        self.card_back = None
        self.card_back_rotated = None
        self.load_images()

    def load_images(self):
        CARD_IMAGES = {
            ("Denari", "A"): "cards/01_Asso_di_denari.jpg",
            ("Denari", "2"): "cards/02_Due_di_denari.jpg",
            ("Denari", "3"): "cards/03_Tre_di_denari.jpg",
            ("Denari", "4"): "cards/04_Quattro_di_denari.jpg",
            ("Denari", "5"): "cards/05_Cinque_di_denari.jpg",
            ("Denari", "6"): "cards/06_Sei_di_denari.jpg",
            ("Denari", "7"): "cards/07_Sette_di_denari.jpg",
            ("Denari", "Fante"): "cards/08_Otto_di_denari.jpg",
            ("Denari", "Cavallo"): "cards/09_Nove_di_denari.jpg",
            ("Denari", "Re"): "cards/10_Dieci_di_denari.jpg",
            ("Coppe", "A"): "cards/11_Asso_di_coppe.jpg",
            ("Coppe", "2"): "cards/12_Due_di_coppe.jpg",
            ("Coppe", "3"): "cards/13_Tre_di_coppe.jpg",
            ("Coppe", "4"): "cards/14_Quattro_di_coppe.jpg",
            ("Coppe", "5"): "cards/15_Cinque_di_coppe.jpg",
            ("Coppe", "6"): "cards/16_Sei_di_coppe.jpg",
            ("Coppe", "7"): "cards/17_Sette_di_coppe.jpg",
            ("Coppe", "Fante"): "cards/18_Otto_di_coppe.jpg",
            ("Coppe", "Cavallo"): "cards/19_Nove_di_coppe.jpg",
            ("Coppe", "Re"): "cards/20_Dieci_di_coppe.jpg",
            ("Spade", "A"): "cards/21_Asso_di_spade.jpg",
            ("Spade", "2"): "cards/22_Due_di_spade.jpg",
            ("Spade", "3"): "cards/23_Tre_di_spade.jpg",
            ("Spade", "4"): "cards/24_Quattro_di_spade.jpg",
            ("Spade", "5"): "cards/25_Cinque_di_spade.jpg",
            ("Spade", "6"): "cards/26_Sei_di_spade.jpg",
            ("Spade", "7"): "cards/27_Sette_di_spade.jpg",
            ("Spade", "Fante"): "cards/28_Otto_di_spade.jpg",
            ("Spade", "Cavallo"): "cards/29_Nove_di_spade.jpg",
            ("Spade", "Re"): "cards/30_Dieci_di_spade.jpg",
            ("Bastoni", "A"): "cards/31_Asso_di_bastoni.jpg",
            ("Bastoni", "2"): "cards/32_Due_di_bastoni.jpg",
            ("Bastoni", "3"): "cards/33_Tre_di_bastoni.jpg",
            ("Bastoni", "4"): "cards/34_Quattro_di_bastoni.jpg",
            ("Bastoni", "5"): "cards/35_Cinque_di_bastoni.jpg",
            ("Bastoni", "6"): "cards/36_Sei_di_bastoni.jpg",
            ("Bastoni", "7"): "cards/37_Sette_di_bastoni.jpg",
            ("Bastoni", "Fante"): "cards/38_Otto_di_bastoni.jpg",
            ("Bastoni", "Cavallo"): "cards/39_Nove_di_bastoni.jpg",
            ("Bastoni", "Re"): "cards/40_Dieci_di_Bastoni.jpg"
        }
        for (suit, rank), path in CARD_IMAGES.items():
            if os.path.exists(path):
                img = Image.open(path).resize((80, 132), Image.Resampling.LANCZOS)
                self.card_images[(suit, rank)] = ImageTk.PhotoImage(img)
                self.card_images_rotated[(suit, rank)] = ImageTk.PhotoImage(img.rotate(180))
            else:
                print(f"Warning: Image {path} not found")
        if os.path.exists("cards/Carte_Napoletane_retro.jpg"):
            img_back = Image.open("cards/Carte_Napoletane_retro.jpg").resize((80, 132), Image.Resampling.LANCZOS)
            self.card_back = ImageTk.PhotoImage(img_back)
            self.card_back_rotated = ImageTk.PhotoImage(img_back.rotate(180))
        else:
            print("Warning: Card back image not found")

    def get_image(self, card, rotated=False):
        if card is None:
            return self.card_back_rotated if rotated else self.card_back
        return self.card_images_rotated[(card.suit, card.rank)] if rotated else self.card_images[(card.suit, card.rank)]
