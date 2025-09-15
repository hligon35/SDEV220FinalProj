# Tkinter GUI frontend for a restaurant ordering system
# GUI layer with placeholders.
# It runs standalone with minimal scaffolding but is written so the backend team
# can plug in their real Product, Inventory, and Order classes later.

import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List, Tuple, Optional

# --- Constants (tweak if you want) ---
APP_TITLE = "Campus Bites - Order Station"
TAX_RATE = 0.07  # 7% sales tax (example)
LOW_STOCK_THRESHOLD = 3  # color code low stock items


# Dev purposes only. Replace with real backend models.
class Product:
    def __init__(self, pid: int, name: str, price: float, stock: int):
        self.id = pid
        self.name = name
        self.price = price
        self.stock = stock


class Inventory:
    def __init__(self, filename: str = "menu.txt"):
        self.filename = filename
        self.products: List[Product] = []

    def load_products(self):
        # Placeholder: real code should load from file/db
        # Backend will populate self.products with Product instances.
        self.products = []  # leave empty here so backend provides data

    def save_products(self):
        # Placeholder for backend
        pass

    def get_product(self, pid: int) -> Optional[Product]:
        for p in self.products:
            if p.id == pid:
                return p
        return None

    def get_stock(self, pid: int) -> int:
        p = self.get_product(pid)
        return p.stock if p else 0

    def reduce_stock(self, pid: int, qty: int) -> bool:
        # Return True if it worked, False if not enough stock
        p = self.get_product(pid)
        if not p:
            return False
        if qty <= 0:
            return False
        if p.stock >= qty:
            p.stock -= qty
            return True
        return False


class Order:
    def __init__(self):
        # items = list of tuples (Product, qty)
        self.items: List[Tuple[Product, int]] = []

    def add_item(self, product: Product, qty: int):
        self.items.append((product, qty))

    def remove_last_item(self):
        if self.items:
            self.items.pop()

    def total(self) -> float:
        return sum(p.price * q for p, q in self.items)

    def summary(self) -> str:
        lines = ["Receipt Summary:"]
        for p, q in self.items:
            lines.append(f"- {p.name} x{q} @ ${p.price:.2f} = ${p.price * q:.2f}")
        sub = self.total()
        tax = sub * TAX_RATE
        total = sub + tax
        lines.append("")
        lines.append(f"Subtotal: ${sub:.2f}")
        lines.append(f"Tax ({TAX_RATE*100:.0f}%): ${tax:.2f}")
        lines.append(f"Total: ${total:.2f}")
        return "\n".join(lines)


# --- MAIN GUI ---
class RestaurantApp:
    def __init__(self, root: tk.Tk, inventory: Inventory):
        self.root = root
        self.inventory = inventory
        self.order = Order()

        self.root.title(APP_TITLE)
        self.root.geometry("1100x650")

        # Holds category mapping (product id -> simple category string)
        self.pid_to_category = {}
        self.active_category = None  # None means show all

        # Build UI
        self._build_top()
        self._build_left()
        self._build_center()
        self._build_right()

        # Load data and paint
        self.inventory.load_products()  # backend replace
        self._rebuild_categories()      # naive categorization off names
        self.refresh_products()         # left menu list
        self.refresh_stock_display()    # right stock list
        self.update_order_summary()     # calc totals

    # --- UI SETUP ---
    def _build_top(self):
        top = ttk.Frame(self.root, padding=(10, 10))
        top.pack(side=tk.TOP, fill=tk.X)
        lbl = ttk.Label(top, text=APP_TITLE, font=("Segoe UI", 18, "bold"))
        lbl.pack(side=tk.LEFT)

    def _build_left(self):
        left = ttk.Frame(self.root, padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Category buttons
        cat_frame = ttk.LabelFrame(left, text="Categories")
        cat_frame.pack(fill=tk.X, pady=(0, 10))

        btn_all = ttk.Button(cat_frame, text="All", command=lambda: self._on_category(None))
        btn_all.grid(row=0, column=0, padx=5, pady=5)
        self._make_cat_button(cat_frame, "Starters", 0, 1)
        self._make_cat_button(cat_frame, "Mains", 0, 2)
        self._make_cat_button(cat_frame, "Drinks", 0, 3)
        self._make_cat_button(cat_frame, "Desserts", 0, 4)

        # Treeview menu items
        menu_frame = ttk.LabelFrame(left, text="Menu Items")
        menu_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "price", "stock")
        self.menu_tree = ttk.Treeview(menu_frame, columns=columns, show="headings", height=12)
        for col, text, width in [
            ("id", "ID", 60),
            ("name", "Name", 220),
            ("price", "Price", 80),
            ("stock", "Stock", 60),
        ]:
            self.menu_tree.heading(col, text=text)
            self.menu_tree.column(col, width=width, anchor=tk.W if col in ("id", "name") else tk.E)

        yscroll = ttk.Scrollbar(menu_frame, orient=tk.VERTICAL, command=self.menu_tree.yview)
        self.menu_tree.configure(yscrollcommand=yscroll.set)
        self.menu_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Quantity + Add to Order
        qty_frame = ttk.Frame(left)
        qty_frame.pack(fill=tk.X, pady=8)
        ttk.Label(qty_frame, text="Qty:").pack(side=tk.LEFT)
        self.qty_var = tk.StringVar(value="1")
        self.qty_entry = ttk.Entry(qty_frame, textvariable=self.qty_var, width=6)
        self.qty_entry.pack(side=tk.LEFT, padx=6)
        self.add_btn = ttk.Button(qty_frame, text="Add to Order", command=self.add_to_order)
        self.add_btn.pack(side=tk.LEFT, padx=6)

    def _build_center(self):
        center = ttk.Frame(self.root, padding=10)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        order_frame = ttk.LabelFrame(center, text="Current Order")
        order_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("item", "qty", "price", "subtotal")
        self.order_tree = ttk.Treeview(order_frame, columns=columns, show="headings", height=12)
        for col, text, width in [
            ("item", "Item", 220),
            ("qty", "Qty", 60),
            ("price", "Price", 80),
            ("subtotal", "Subtotal", 100),
        ]:
            self.order_tree.heading(col, text=text)
            anchor = tk.W if col == "item" else tk.E
            self.order_tree.column(col, width=width, anchor=anchor)

        yscroll = ttk.Scrollbar(order_frame, orient=tk.VERTICAL, command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=yscroll.set)
        self.order_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Order actions
        actions = ttk.Frame(center)
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Remove Last Item", command=self._on_remove_last).pack(side=tk.LEFT)

        # Totals area
        totals = ttk.LabelFrame(center, text="Totals")
        totals.pack(fill=tk.X)
        self.subtotal_var = tk.StringVar(value="$0.00")
        self.tax_var = tk.StringVar(value="$0.00")
        self.total_var = tk.StringVar(value="$0.00")

        row1 = ttk.Frame(totals)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Subtotal:").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.subtotal_var).pack(side=tk.RIGHT)

        row2 = ttk.Frame(totals)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text=f"Tax ({int(TAX_RATE*100)}%):").pack(side=tk.LEFT)
        ttk.Label(row2, textvariable=self.tax_var).pack(side=tk.RIGHT)

        row3 = ttk.Frame(totals)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Total:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(row3, textvariable=self.total_var, font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT)

        # Checkout / Receipt
        bottom = ttk.Frame(center)
        bottom.pack(fill=tk.X, pady=6)
        ttk.Button(bottom, text="Checkout", command=self._on_checkout).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Print Receipt", command=self._on_print_receipt).pack(side=tk.LEFT, padx=4)

    def _build_right(self):
        right = ttk.Frame(self.root, padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        stock_frame = ttk.LabelFrame(right, text="Stock Levels")
        stock_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "name", "stock")
        self.stock_tree = ttk.Treeview(stock_frame, columns=columns, show="headings", height=12)
        for col, text, width in [
            ("id", "ID", 60),
            ("name", "Name", 220),
            ("stock", "Stock", 60),
        ]:
            self.stock_tree.heading(col, text=text)
            self.stock_tree.column(col, width=width, anchor=tk.W if col in ("id", "name") else tk.E)

        # Setup row color tags for low-stock
        self.stock_tree.tag_configure("low", background="#ffe5e5")  # light red

        yscroll = ttk.Scrollbar(stock_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=yscroll.set)
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Stock actions
        actions = ttk.LabelFrame(right, text="Actions")
        actions.pack(fill=tk.X, pady=8)
        ttk.Button(actions, text="Send to Kitchen", command=self._on_send_to_kitchen).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(actions, text="Hold Order", command=self._on_hold_order).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(actions, text="Cancel Order", command=self._on_cancel_order).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ttk.Button(actions, text="Load Menu", command=self._on_load_menu).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(actions, text="Update Stock", command=self._on_update_stock).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Label(actions, text="").grid(row=1, column=2, padx=4, pady=4, sticky="ew")

    def _make_cat_button(self, parent, label, row, col):
        ttk.Button(parent, text=label, command=lambda l=label: self._on_category(l)).grid(row=row, column=col, padx=5, pady=5)

    # --- Category helpers ---
    def _rebuild_categories(self):
        # Helper: guesses categories based on product names.
        # Can be replaced if not needed.
        self.pid_to_category = {}
        for p in self.inventory.products:
            name = p.name.lower()
            if any(x in name for x in ["soup", "salad", "starter"]):
                cat = "Starters"
            elif any(x in name for x in ["tea", "cola", "coffee", "water", "drink"]):
                cat = "Drinks"
            elif any(x in name for x in ["cake", "pie", "ice cream", "dessert"]):
                cat = "Desserts"
            else:
                cat = "Mains"
            self.pid_to_category[p.id] = cat

    def _on_category(self, category_name: Optional[str]):
        self.active_category = category_name
        self.refresh_products()

    # --- Refresh displays ---
    def refresh_products(self):
        # Populate left menu based on current category filter
        for row in self.menu_tree.get_children():
            self.menu_tree.delete(row)

        for p in self.inventory.products:
            if self.active_category and self.pid_to_category.get(p.id) != self.active_category:
                continue
            self.menu_tree.insert("", tk.END, iid=str(p.id), values=(p.id, p.name, f"${p.price:.2f}", p.stock))

    def refresh_stock_display(self):
        # Populate right stock list with color-coded low stock
        for row in self.stock_tree.get_children():
            self.stock_tree.delete(row)

        for p in self.inventory.products:
            tags = ("low",) if p.stock <= LOW_STOCK_THRESHOLD else ()
            self.stock_tree.insert("", tk.END, iid=str(p.id), values=(p.id, p.name, p.stock), tags=tags)

    # --- ORDER LOGIC ---
    def add_to_order(self):
        # Grab selected menu item
        selected = self.menu_tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Please pick a menu item first.")
            return
        pid = int(selected[0])
        product = self.inventory.get_product(pid)
        if not product:
            messagebox.showerror("Error", "Could not find the selected product.")
            return

        # Quantity validation (simple)
        try:
            qty = int(self.qty_var.get())
        except ValueError:
            messagebox.showwarning("Bad quantity", "Please enter a whole number for quantity.")
            return
        if qty <= 0:
            messagebox.showwarning("Bad quantity", "Quantity should be at least 1.")
            return

        # Reduce stock only at checkout in case of cancellation
        self.order.add_item(product, qty)

        # Update order table and totals
        self._refresh_order_table()
        self.update_order_summary()

    def _refresh_order_table(self):
        for row in self.order_tree.get_children():
            self.order_tree.delete(row)
        for idx, (p, q) in enumerate(self.order.items, start=1):
            subtotal = p.price * q
            self.order_tree.insert("", tk.END, iid=str(idx), values=(p.name, q, f"${p.price:.2f}", f"${subtotal:.2f}"))

    def _on_remove_last(self):
        self.order.remove_last_item()
        self._refresh_order_table()
        self.update_order_summary()

    def update_order_summary(self):
        # Calculate subtotal, tax, total
        subtotal = self.order.total()
        tax = subtotal * TAX_RATE
        total = subtotal + tax

        self.subtotal_var.set(f"${subtotal:.2f}")
        self.tax_var.set(f"${tax:.2f}")
        self.total_var.set(f"${total:.2f}")

    # --- ACTIONS: checkout, print, kitchen, etc. ---
    def _on_checkout(self):
        if not self.order.items:
            messagebox.showinfo("Empty order", "Add some items before checking out.")
            return

        # Confirm total
        subtotal = self.order.total()
        tax = subtotal * TAX_RATE
        total = subtotal + tax
        if not messagebox.askyesno("Confirm Checkout", f"Total with tax: ${total:.2f}\n\nProceed to checkout?"):
            return

        # Reduce stock for each item; any fails, show an error.
        # Hit a mid-day stock issue, don't roll back to keep it simple.
        for p, q in self.order.items:
            ok = self.inventory.reduce_stock(p.id, q)
            if not ok:
                messagebox.showwarning(
                    "Stock low",
                    f"We couldn't reserve {q} of {p.name}. Available: {self.inventory.get_stock(p.id)}.\n\nPlease adjust the order.",
                )
                # Stop here for fix
                break
        else:
            # All good, clear order
            messagebox.showinfo("Success", "Payment complete. Order confirmed!")
            self.order = Order()
            self._refresh_order_table()
            self.update_order_summary()
            self.refresh_products()
            self.refresh_stock_display()

    def _on_print_receipt(self):
        if not self.order.items:
            messagebox.showinfo("Nothing to print", "There's no receipt to print yet.")
            return
        # Preview window with text
        win = tk.Toplevel(self.root)
        win.title("Receipt Preview")
        win.geometry("400x400")

        text = tk.Text(win, wrap="word")
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", self.order.summary())
        text.configure(state=tk.DISABLED)

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def _on_send_to_kitchen(self):
        # Notify the kitchen, (or just a popup)
        if not self.order.items:
            messagebox.showinfo("No items", "Add items before sending to kitchen.")
            return
        messagebox.showinfo("Sent", "Order was sent to the kitchen (pretend).")

    def _on_hold_order(self):
        if not self.order.items:
            messagebox.showinfo("No items", "There's nothing to hold yet.")
            return
        messagebox.showinfo("Held", "Order is on hold (no inventory changes yet).")

    def _on_cancel_order(self):
        if not self.order.items:
            messagebox.showinfo("Already empty", "There's no active order to cancel.")
            return
        if messagebox.askyesno("Cancel Order", "Clear the current order?"):
            self.order = Order()
            self._refresh_order_table()
            self.update_order_summary()

    def _on_load_menu(self):
        # Placeholder to re-load product list
        self.inventory.load_products()
        self._rebuild_categories()
        self.refresh_products()
        self.refresh_stock_display()

    def _on_update_stock(self):
        # Lets user pick item in stock table and set new quantity
        selected = self.stock_tree.selection()
        if not selected:
            messagebox.showinfo("Pick item", "Select an item in the Stock table first.")
            return
        pid = int(selected[0])
        product = self.inventory.get_product(pid)
        if not product:
            messagebox.showerror("Error", "Couldn't find that product.")
            return

        new_stock = simpledialog.askinteger("Update Stock", f"Set stock for {product.name} (current {product.stock}):", minvalue=0)
        if new_stock is None:
            return  # user canceled
        product.stock = new_stock
        self.inventory.save_products()  # placeholder
        self.refresh_products()
        self.refresh_stock_display()


# --- ENTRY POINT ---
if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()

    # Change to read from a file or db
    inv = Inventory()

    app = RestaurantApp(root, inv)

    try:
        style = ttk.Style()
        if os.name == "nt":
            style.theme_use("vista")
        else:
            style.theme_use("clam")
    except Exception:
        pass

    root.mainloop()
