import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from PIL import Image, ImageTk
import json
import glob
import threading
import queue

class DeckBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deck Builder")
        self.root.geometry("1920x1080")  # Adjust the window size as needed

        # Connect to the SQLite database
        self.conn = sqlite3.connect('cards.db')
        self.c = self.conn.cursor()

        print("Initializing...")

        # Card image caches
        self.card_images = {}
        self.original_images = {}

        # Queue for thread-safe image loading
        self.image_queue = queue.Queue()

        # Load card metadata (without images)
        self.cards = self.load_card_metadata()

        print("Initialization done.")

        # Create the GUI widgets
        self.create_widgets()

        self.deck_count = {}
        self.evolved_deck_count = {}

        # Start a thread to process the image queue
        self.image_thread = threading.Thread(target=self.process_image_queue)
        self.image_thread.daemon = True
        self.image_thread.start()

    def load_card_metadata(self):
        # Load card metadata from the database
        self.c.execute("SELECT name, code FROM cards")
        cards = self.c.fetchall()
        return {card[0]: card[1] for card in cards}

    def load_card_image(self, card_name):
        # Load a single card image (called lazily)
        code = self.cards[card_name]
        try:
            image = Image.open(f"card_images/{code}.png")
            self.original_images[card_name] = ImageTk.PhotoImage(image)
            image2 = Image.open(f"card_images/{code}_mini.png")
            self.card_images[card_name] = ImageTk.PhotoImage(image2)
        except FileNotFoundError:
            print(f"Image not found for card: {card_name}")
            self.card_images[card_name] = None
            self.original_images[card_name] = None
        except Exception as e:
            print(f"Error loading image for card {card_name}: {e}")

    def create_widgets(self):
        # Create the filter frames
        filter_frame1 = tk.Frame(self.root)
        filter_frame1.pack(fill=tk.X, padx=5, pady=5)
        
        filter_frame2 = tk.Frame(self.root)
        filter_frame2.pack(fill=tk.X, padx=5, pady=5)

        # Class filter
        self.class_label = ttk.Label(filter_frame1, text="Class:")
        self.class_label.pack(side=tk.LEFT)

        self.class_var = tk.StringVar(value="All")
        self.class_combobox = ttk.Combobox(filter_frame1, textvariable=self.class_var)
        self.class_combobox['values'] = ["All"] + self.get_class()
        self.class_combobox.pack(side=tk.LEFT, padx=5)
        self.class_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Name filter
        self.name_filter_label = ttk.Label(filter_frame1, text="Filter by Name:")
        self.name_filter_label.pack(side=tk.LEFT)

        self.name_filter_entry = ttk.Entry(filter_frame1)
        self.name_filter_entry.pack(side=tk.LEFT, padx=5)
        self.name_filter_entry.bind("<KeyRelease>", self.update_card_list)

        # Type filter
        self.type_filter_label = ttk.Label(filter_frame1, text="Filter by Type:")
        self.type_filter_label.pack(side=tk.LEFT)

        self.type_var = tk.StringVar()
        self.type_combobox = ttk.Combobox(filter_frame1, textvariable=self.type_var)
        self.type_combobox['values'] = ["", "Follower", "Spell", "Amulet"]
        self.type_combobox.pack(side=tk.LEFT, padx=5)
        self.type_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Universe filter
        self.universe_filter_label = ttk.Label(filter_frame1, text="Filter by Universe:")
        self.universe_filter_label.pack(side=tk.LEFT)

        self.universe_var = tk.StringVar()
        self.universe_combobox = ttk.Combobox(filter_frame1, textvariable=self.universe_var)
        self.universe_combobox['values'] = ["", "Shadowverse", "Umamusume", "Cinderella Girls"]
        self.universe_combobox.pack(side=tk.LEFT, padx=5)
        self.universe_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Rarity filter
        self.rarity_filter_label = ttk.Label(filter_frame2, text="Filter by Rarity:")
        self.rarity_filter_label.pack(side=tk.LEFT)

        self.rarity_var = tk.StringVar()
        self.rarity_combobox = ttk.Combobox(filter_frame2, textvariable=self.rarity_var)
        self.rarity_combobox['values'] = ["", "Legendary", "Gold", "Silver", "Bronze"]
        self.rarity_combobox.pack(side=tk.LEFT, padx=5)
        self.rarity_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Evolved filter
        self.evolved_filter_label = ttk.Label(filter_frame2, text="Filter by Evolved:")
        self.evolved_filter_label.pack(side=tk.LEFT)

        self.evolved_var = tk.StringVar()
        self.evolved_combobox = ttk.Combobox(filter_frame2, textvariable=self.evolved_var)
        self.evolved_combobox['values'] = ["", "Base", "Evolve"]
        self.evolved_combobox.pack(side=tk.LEFT, padx=5)
        self.evolved_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Cost filter
        self.cost_filter_label = ttk.Label(filter_frame2, text="Filter by Cost:")
        self.cost_filter_label.pack(side=tk.LEFT)

        self.cost_var = tk.StringVar(value="All")
        self.cost_combobox = ttk.Combobox(filter_frame2, textvariable=self.cost_var, state="readonly")
        self.cost_combobox['values'] = ["All"] + list(range(16))
        self.cost_combobox.pack(side=tk.LEFT, padx=5)
        self.cost_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Trait filter
        self.trait_filter_label = ttk.Label(filter_frame2, text="Filter by Trait:")
        self.trait_filter_label.pack(side=tk.LEFT)

        self.trait_filter_entry = ttk.Entry(filter_frame2)
        self.trait_filter_entry.pack(side=tk.LEFT, padx=5)
        self.trait_filter_entry.bind("<KeyRelease>", self.update_card_list)

        # Show only cards in deck filter
        self.show_only_in_deck_var = tk.BooleanVar()
        self.show_only_in_deck_checkbutton = ttk.Checkbutton(
            filter_frame2, text="Show only cards in deck", variable=self.show_only_in_deck_var, command=self.update_card_list)
        self.show_only_in_deck_checkbutton.pack(side=tk.LEFT, padx=5)

        # Sort option
        self.sort_label = ttk.Label(filter_frame2, text="Sort by:")
        self.sort_label.pack(side=tk.LEFT)

        self.sort_var = tk.StringVar(value="Cost")
        self.sort_combobox = ttk.Combobox(filter_frame2, textvariable=self.sort_var, state="readonly")
        self.sort_combobox['values'] = ["Cost", "Alphabetical", "Release Order"]
        self.sort_combobox.pack(side=tk.LEFT, padx=5)
        self.sort_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Card set filter 
        self.card_set_label = ttk.Label(filter_frame2, text="Filter by Card Set:")
        self.card_set_label.pack(side=tk.LEFT)

        self.card_set_var = tk.StringVar(value="All")
        self.card_set_combobox = ttk.Combobox(filter_frame2, textvariable=self.card_set_var, state="readonly")
        self.card_set_combobox['values'] = ["All"] + self.get_card_sets()
        self.card_set_combobox.pack(side=tk.LEFT, padx=5) 
        self.card_set_combobox.bind("<<ComboboxSelected>>", self.update_card_list)

        # Frame for cards and scrollbar
        self.card_frame = tk.Frame(self.root)
        self.card_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.LEFT)

        self.canvas = tk.Canvas(self.card_frame)
        self.scrollbar = ttk.Scrollbar(self.card_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Add mousewheel support
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Main frame to contain both deck_frame and evolved_deck_frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, side=tk.LEFT, padx=5, pady=5)

        # Frame for deck
        self.deck_frame = tk.Frame(self.main_frame)
        self.deck_frame.pack(fill=tk.BOTH, side=tk.TOP, padx=5, pady=5)

        self.deck_label = ttk.Label(self.deck_frame, text="Deck (0 cards)")
        self.deck_label.pack()

        # Increase the width of the deck listbox
        self.deck_listbox = tk.Listbox(self.deck_frame, height=20, width=50)
        self.deck_listbox.pack(fill=tk.BOTH, expand=True)
        self.deck_listbox.bind("<Double-Button-1>", self.remove_from_deck)

        # Frame for evolved deck
        self.evolved_deck_frame = tk.Frame(self.main_frame)
        self.evolved_deck_frame.pack(fill=tk.BOTH, side=tk.TOP, padx=5, pady=5)

        self.evolved_deck_label = ttk.Label(self.evolved_deck_frame, text="Evolved Deck (0 cards)")
        self.evolved_deck_label.pack()

        # Increase the width of the evolved deck listbox
        self.evolved_deck_listbox = tk.Listbox(self.evolved_deck_frame, height=20, width=50)
        self.evolved_deck_listbox.pack(fill=tk.BOTH, expand=True)
        self.evolved_deck_listbox.bind("<Double-Button-1>", self.remove_from_evolved_deck)

        # Frame for buttons
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        # Clear deck button
        self.clear_deck_button = ttk.Button(button_frame, text="Clear", command=self.clear_decks)
        self.clear_deck_button.pack(side=tk.LEFT, padx=5)

        # Export deck button
        self.export_deck_button = ttk.Button(button_frame, text="Export Deck", command=self.export_deck)
        self.export_deck_button.pack(side=tk.LEFT, padx=5)

        # Import deck button
        self.import_deck_button = ttk.Button(button_frame, text="Import Deck", command=self.import_deck)
        self.import_deck_button.pack(side=tk.LEFT, padx=5)

        # Labels for displaying total counts of Spells, Amulets, and Followers
        self.deck_totals_label = ttk.Label(self.deck_frame, text="Spells: 0, Amulets: 0, Followers: 0")
        self.deck_totals_label.pack()

    def get_class(self):
        # Retrieve distinct classes from the database
        self.c.execute("SELECT DISTINCT class FROM cards")
        classes = [row[0] for row in self.c.fetchall()]
        return classes

    def get_card_sets(self):
        # Retrieve distinct card sets from the database
        self.c.execute("SELECT DISTINCT card_set FROM cards")
        sets = [row[0] for row in self.c.fetchall()]
        return sets

    def update_card_list(self, *args):
        # Update the card list based on the selected filters and sort option
        selected_class = self.class_var.get()
        name_filter = self.name_filter_entry.get().strip()
        type_filter = self.type_var.get().strip()
        universe_filter = self.universe_var.get().strip()
        rarity_filter = self.rarity_var.get().strip()
        evolved_filter = self.evolved_var.get().strip()
        cost_filter = self.cost_var.get()
        trait_filter = self.trait_filter_entry.get().strip()
        show_only_in_deck = self.show_only_in_deck_var.get()
        sort_option = self.sort_var.get()
        card_set_filter = self.card_set_var.get().strip()

        query = "SELECT name, cost FROM cards WHERE 1=1"
        parameters = []

        if selected_class != "All":
            query += " AND class=?"
            parameters.append(selected_class)
        if name_filter:
            query += " AND name LIKE ?"
            parameters.append(f"%{name_filter}%")
        if type_filter:
            query += " AND type=?"
            parameters.append(type_filter)
        if universe_filter:
            query += " AND universe=?"
            parameters.append(universe_filter)
        if card_set_filter != "All":
            query += " AND card_set=?"
            parameters.append(card_set_filter)
        if rarity_filter:
            query += " AND rarity=?"
            parameters.append(rarity_filter)
        if evolved_filter:
            if evolved_filter == "Base":
                query += " AND evolved=?"
                parameters.append("no")
            elif evolved_filter == "Evolve":
                query += " AND evolved=?"
                parameters.append("yes")
        if cost_filter != "All":
            query += " AND cost=?"
            parameters.append(cost_filter)
        if trait_filter:
            query += " AND trait LIKE ?"
            parameters.append(f"%{trait_filter}%")
        if show_only_in_deck:
            cards_in_deck = list(self.deck_count.keys()) + list(self.evolved_deck_count.keys())
            if cards_in_deck:
                query += " AND name IN ({seq})".format(seq=','.join(['?']*len(cards_in_deck)))
                parameters.extend(cards_in_deck)

        self.c.execute(query, parameters)
        cards = self.c.fetchall()

        if sort_option == "Cost":
            cards.sort(key=lambda x: x[1])
        elif sort_option == "Alphabetical":
            cards.sort(key=lambda x: x[0])

        # Clear the current card display
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Display the cards in a grid (with 9 columns per row)
        self.card_labels = {}
        for i, (card, cost) in enumerate(cards):
            if card not in self.card_images:
                # Lazy load the image
                self.image_queue.put(card)
            if card in self.card_images and self.card_images[card]:
                card_label = ttk.Label(self.scrollable_frame, image=self.card_images[card])
                card_label.image = self.card_images[card]
                card_label.grid(row=i // 9, column=i % 9, padx=5, pady=5)
                card_label.bind("<Button-1>", lambda e, card=card: self.add_to_deck(e, card))
                card_label.bind("<Button-2>", lambda e, card=card: self.show_large_image(e, card))  # Scroll wheel click
                card_label.bind("<Button-3>", lambda e, card=card: self.remove_card_from_deck(e, card))  # Right click
                card_label.bind("<Enter>", lambda e, card=card: self.show_card_name(e, card))
                card_label.bind("<Leave>", lambda e: self.hide_card_name(e))
                if card in self.deck_count or card in self.evolved_deck_count:
                    card_label.config(borderwidth=2, relief="solid", background="yellow")
                self.card_labels[card] = card_label
            else:
                card_label = ttk.Label(self.scrollable_frame, text=card)
                card_label.grid(row=i // 9, column=i % 9, padx=5, pady=5)
                card_label.bind("<Button-1>", lambda e, card=card: self.add_to_deck(e, card))
                card_label.bind("<Button-2>", lambda e, card=card: self.show_large_image(e, card))  # Scroll wheel click
                card_label.bind("<Button-3>", lambda e, card=card: self.remove_card_from_deck(e, card))  # Right click
                card_label.bind("<Enter>", lambda e, card=card: self.show_card_name(e, card))
                card_label.bind("<Leave>", lambda e: self.hide_card_name(e))
                if card in self.deck_count or card in self.evolved_deck_count:
                    card_label.config(borderwidth=2, relief="solid", background="yellow")
                self.card_labels[card] = card_label

    def process_image_queue(self):
        while True:
            card = self.image_queue.get()
            if card is None:
                break
            self.load_card_image(card)
            self.root.after(0, self.update_card_label, card)
            self.image_queue.task_done()

    def update_card_label(self, card):
        if card in self.card_labels and self.card_images[card]:
            self.card_labels[card].config(image=self.card_images[card])
            self.card_labels[card].image = self.card_images[card]

    def add_to_deck(self, event, card):
        # Add a card to the deck
        if self.get_card_evolved(card) == "yes":
            evolved_deck_count = self.evolved_deck_count.get(card, 0)
            if evolved_deck_count < 3:
                self.evolved_deck_count[card] = evolved_deck_count + 1
                self.update_deck_display()
                self.update_card_background(card)
        else:
            deck_count = self.deck_count.get(card, 0)
            if deck_count < 3:
                self.deck_count[card] = deck_count + 1
                self.update_deck_display()
                self.update_card_background(card)

    def remove_from_deck(self, event):
        # Remove a card from the deck
        selection = self.deck_listbox.curselection()
        if selection:
            card = self.deck_listbox.get(selection[0]).split(') ')[1].split(' (')[0]
            deck_count = self.deck_count.get(card, 0)
            if deck_count > 0:
                self.deck_count[card] -= 1
                if self.deck_count[card] == 0:
                    del self.deck_count[card]
            self.update_deck_display()
            self.update_card_background(card)

    def remove_from_evolved_deck(self, event):
        # Remove a card from the evolved deck
        selection = self.evolved_deck_listbox.curselection()
        if selection:
            # Extract the entire card name including (Evolved)
            selected_item = self.evolved_deck_listbox.get(selection[0])
            card_parts = selected_item.split(' (')
            card = ' ('.join(card_parts[:-1]).split(') ')[1]
            print(f"Selected item: {selected_item}")
            print(f"Card to remove: {card}")

            evolved_deck_count = self.evolved_deck_count.get(card, 0)
            if evolved_deck_count > 0:
                self.evolved_deck_count[card] -= 1
                if self.evolved_deck_count[card] == 0:
                    del self.evolved_deck_count[card]
            self.update_deck_display()
            self.update_card_background(card)

    def remove_card_from_deck(self, event, card):
        # Remove a card from the deck or evolved deck by right-clicking
        if self.get_card_evolved(card) == "yes":
            evolved_deck_count = self.evolved_deck_count.get(card, 0)
            if evolved_deck_count > 0:
                self.evolved_deck_count[card] -= 1
                if self.evolved_deck_count[card] == 0:
                    del self.evolved_deck_count[card]
        else:
            deck_count = self.deck_count.get(card, 0)
            if deck_count > 0:
                self.deck_count[card] -= 1
                if self.deck_count[card] == 0:
                    del self.deck_count[card]
        self.update_deck_display()
        self.update_card_background(card)

    def show_large_image(self, event, card):
        # Show the original version of the card in a new window
        if card in self.original_images:
            original_image = self.original_images[card]
            if original_image:
                large_image_window = tk.Toplevel(self.root)
                large_image_window.title(card)
                large_image_label = ttk.Label(large_image_window, image=original_image)
                large_image_label.image = original_image
                large_image_label.pack()

    def update_deck_display(self):
        # Update the display of the deck and evolved deck
        self.deck_listbox.delete(0, tk.END)
        self.evolved_deck_listbox.delete(0, tk.END)

        # Update regular deck display
        sorted_deck = sorted(self.deck_count.items(), key=lambda x: self.get_card_cost(x[0]))
        for card, count in sorted_deck:
            card_cost = self.get_card_cost(card)
            display_name = f"({card_cost}) {card}"
            self.deck_listbox.insert(tk.END, f"{display_name} ({count})")

        # Update evolved deck display
        sorted_evolved_deck = sorted(self.evolved_deck_count.items(), key=lambda x: self.get_card_cost(x[0]))
        for card, count in sorted_evolved_deck:
            card_cost = self.get_card_cost(card)
            display_name = f"({card_cost}) {card}"
            self.evolved_deck_listbox.insert(tk.END, f"{display_name} ({count})")

        # Update deck and evolved deck labels with the card counts
        total_deck_cards = sum(self.deck_count.values())
        total_evolved_cards = sum(self.evolved_deck_count.values())
        self.deck_label.config(text=f"Deck ({total_deck_cards} cards)")
        self.evolved_deck_label.config(text=f"Evolved Deck ({total_evolved_cards} cards)")

        # Update the counts of Spells, Amulets, and Followers
        self.update_totals()

    def update_card_background(self, card):
        # Update the background color of card images without refreshing the whole card list
        if card in self.card_labels:
            if card in self.deck_count or card in self.evolved_deck_count:
                self.card_labels[card].config(background="yellow")
            else:
                self.card_labels[card].config(background="")

    def update_totals(self):
        # Update the counts of Spells, Amulets, and Followers in the regular deck
        spell_count = sum(count for card, count in self.deck_count.items() if self.get_card_type(card) == "Spell")
        amulet_count = sum(count for card, count in self.deck_count.items() if self.get_card_type(card) == "Amulet")
        follower_count = sum(count for card, count in self.deck_count.items() if self.get_card_type(card) == "Follower")
        self.deck_totals_label.config(text=f"Spells: {spell_count}, Amulets: {amulet_count}, Followers: {follower_count}")

    def get_card_type(self, card_name):
        # Retrieve the type of a card from the database
        self.c.execute("SELECT type FROM cards WHERE name=?", (card_name,))
        result = self.c.fetchone()
        return result[0] if result else ""

    def get_card_cost(self, card_name):
        # Retrieve the cost of a card from the database
        self.c.execute("SELECT cost FROM cards WHERE name=?", (card_name,))
        result = self.c.fetchone()
        return result[0] if result else 0

    def get_card_evolved(self, card_name):
        # Retrieve if a card is evolved from the database
        self.c.execute("SELECT evolved FROM cards WHERE name=?", (card_name,))
        result = self.c.fetchone()
        return result[0] if result else 'no'

    def export_deck(self):
        # Export the current deck to a text file
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, "w") as file:
                file.write("Deck:\n")
                for card_name, count in self.deck_count.items():
                    file.write(f"x{count} {card_name} \n")
                file.write("\nEvolved Deck:\n")
                for card_name, count in self.evolved_deck_count.items():
                    file.write(f"x{count} {card_name} \n")
            messagebox.showinfo("Export Deck", f"Deck has been exported to {filename}")

    def import_deck(self):
        # Import a deck from a text file
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                with open(filename, "r") as file:
                    content = file.read().splitlines()
                self.deck_count.clear()
                self.evolved_deck_count.clear()
                current_dict = None
                for line in content:
                    if line.startswith("Deck:"):
                        current_dict = self.deck_count
                    elif line.startswith("Evolved Deck:"):
                        current_dict = self.evolved_deck_count
                    elif line.startswith("x"):
                        count, card_name = line.split(" ", 1)
                        card_name = card_name.strip()
                        count = int(count[1:])
                        if current_dict is not None:
                            current_dict[card_name] = count
                self.update_deck_display()
                self.update_card_list()
                messagebox.showinfo("Import Deck", f"Deck has been imported from {filename}")
            except FileNotFoundError:
                messagebox.showerror("Import Deck", "File not found")

    def clear_decks(self):
        # Clear both the regular and evolved decks
        self.deck_count.clear()
        self.evolved_deck_count.clear()
        self.update_deck_display()
        self.update_card_list()

    def _on_mousewheel(self, event):
        # Scroll the canvas with the mouse wheel
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def show_card_name(self, event, card_name):
        # Display the card name as a tooltip when hovering over the card image
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        x, y = event.widget.winfo_pointerxy()
        self.tooltip.geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=card_name, background="black", foreground="white", relief="solid", borderwidth=1)
        label.pack()

    def hide_card_name(self, event):
        # Hide the tooltip when not hovering over the card image
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()

def parse_card_file(filenames):
    # Parse the card data from JSON files
    cards = []
    for filename in filenames:
        with open(filename, 'r') as file:
            card_data = json.load(file)
        for card in card_data:
            cards.append(card)
    return cards

def create_database(cards, db_name='cards.db'):
    # Create the SQLite database and populate it with card data
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS cards''')
    c.execute('''CREATE TABLE cards
                 (name TEXT, cost INTEGER, attack INTEGER, defense INTEGER, type TEXT, 
                 universe TEXT, rarity TEXT, code TEXT, class TEXT, trait TEXT, evolved TEXT, card_set TEXT)''')
    for card in cards:
        c.execute('''INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', 
              (card['name'], int(card.get('cost', 0)), 
               int(card.get('attack', None)) if card.get('attack') else None,
               int(card.get('defense', None)) if card.get('defense') else None,
               card['type'], card['universe'], card['rarity'], card['code'], 
               card['class'], card.get('trait', ''), card['evolved'], card.get('card_set', '')))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Load card data and create the database
    card_files = glob.glob("sets_db/*.json")
    cards = parse_card_file(card_files)
    create_database(cards)

    # Create the main application window and run the application
    root = tk.Tk()
    app = DeckBuilderApp(root)
    root.mainloop()
