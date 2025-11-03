import tkinter as tk
import math
from tkinter import ttk, messagebox, font
import threading
import mysql.connector
from datetime import datetime
from escpos.printer import Serial
from PIL import Image, ImageDraw, ImageFont

# ---------------- MySQL Connection ----------------
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="cash_trader"
    )
    cursor = conn.cursor()
except Exception as e:
    messagebox.showerror("DB Connection Error", str(e))
    exit()

# ---------------- Main Window ----------------
root = tk.Tk()
root.state('zoomed')
root.title("Wholesale Shop POS - CASH TRADER")
global_font = font.Font(family="Arial", size=13)

style = ttk.Style()
style.configure("Treeview", font=("Arial", 12))
# ---------------- Product Management ----------------
def fetch_products():
    cursor.execute("SELECT id, name_en, name_hi, price FROM products ORDER BY name_en ASC")
    rows = cursor.fetchall()
    product_tree.delete(*product_tree.get_children())
    for row in rows:
        product_tree.insert("", tk.END, values=row)

def add_product():
    name_en, name_hi = name_en_entry.get(), name_hi_entry.get()
    try:
        price = float(price_entry.get())
    except:
        return messagebox.showerror("Error", "Price must be a number")
    if not (name_en and name_hi):
        return messagebox.showerror("Error", "Fill all fields")
    try:
        cursor.execute("INSERT INTO products (name_en, name_hi, price) VALUES (%s,%s,%s)",
                       (name_en, name_hi, price))
        conn.commit()
        fetch_products()
        clear_inputs()
    except mysql.connector.IntegrityError:
        messagebox.showerror("Error", "Product must be unique")

def update_product():
    selected = product_tree.selection()
    if not selected:
        return messagebox.showerror("Error", "Select a product to update")
    item = product_tree.item(selected)
    product_id = item['values'][0]
    name_en, name_hi = name_en_entry.get(), name_hi_entry.get()
    try:
        price = float(price_entry.get())
    except:
        return messagebox.showerror("Error", "Price must be a number")
    if not (name_en and name_hi):
        return messagebox.showerror("Error", "Fill all fields")
    try:
        cursor.execute("UPDATE products SET name_en=%s, name_hi=%s, price=%s WHERE id=%s",
                       (name_en, name_hi, price, product_id))
        conn.commit()
        fetch_products()
        clear_inputs()
    except mysql.connector.IntegrityError:
        messagebox.showerror("Error", "Product must be unique")

def delete_product():
    selected = product_tree.selection()
    if not selected:
        return messagebox.showerror("Error", "Select a product to delete")
    item = product_tree.item(selected)
    product_id = item['values'][0]
    if messagebox.askyesno("Confirm Delete", "Are you sure?"):
        cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
        conn.commit()
        fetch_products()
        clear_inputs()

def clear_inputs():
    for e in [name_en_entry, name_hi_entry, price_entry]:
        e.delete(0, tk.END)

def select_product(event):
    selected = product_tree.selection()
    if selected:
        item = product_tree.item(selected)
        name_en_entry.delete(0, tk.END)
        name_hi_entry.delete(0, tk.END)
        price_entry.delete(0, tk.END)
        name_en_entry.insert(0, item['values'][1])
        name_hi_entry.insert(0, item['values'][2])
        price_entry.insert(0, item['values'][3])

# ---------------- Product Management UI ----------------
pm_frame = tk.Frame(root)
pm_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)

tk.Label(pm_frame, text="Product Management", font=("Arial",18)).grid(row=0, column=0, columnspan=2, pady=5)
tk.Label(pm_frame, text="Name (English)", font=global_font).grid(row=1, column=0, pady=5)
tk.Label(pm_frame, text="Name (Hindi)", font=global_font).grid(row=2, column=0, pady=5)
tk.Label(pm_frame, text="Price", font=global_font).grid(row=3, column=0, pady=5)

name_en_entry = tk.Entry(pm_frame, font=global_font)
name_hi_entry = tk.Entry(pm_frame, font=global_font)
price_entry = tk.Entry(pm_frame, font=global_font)
name_en_entry.grid(row=1, column=1)
name_hi_entry.grid(row=2, column=1)
price_entry.grid(row=3, column=1)

tk.Button(pm_frame, text="Add", font=global_font, width=12, command=add_product).grid(row=4, column=0, pady=5)
tk.Button(pm_frame, text="Update", font=global_font, width=12, command=update_product).grid(row=4, column=1, pady=5)
tk.Button(pm_frame, text="Delete", font=global_font, width=12, command=delete_product).grid(row=5, column=0, pady=5)
tk.Button(pm_frame, text="Clear", font=global_font, width=12, command=clear_inputs).grid(row=5, column=1, pady=5)

# Suggestion box
suggestion_box = tk.Listbox(pm_frame, font=global_font, height=26, width=34)
suggestion_box.grid(row=6, column=0, columnspan=2, pady=5)

# Treeview for products
heading_font = font.Font(family="Arial", size=12, weight="bold")
style = ttk.Style()
style.configure("Treeview.Heading", font=heading_font)

product_tree = ttk.Treeview(root, columns=("ID","Name_EN", "Name_HI", "Price"), show="headings", height=10)
for col, text in zip(("ID","Name_EN", "Name_HI", "Price"), ("ID","Name (English)", "Name (Hindi)", "Price")):
    product_tree.heading(col, text=text)
product_tree.pack(side=tk.TOP, fill=tk.X, padx=30, pady=10)
product_tree.bind("<ButtonRelease-1>", select_product)
fetch_products()

# ---------------- Billing ----------------
bill_items = {}
editing_entry = None

bill_frame = tk.Frame(root)
bill_frame.pack(side=tk.BOTTOM, padx=90, pady=10, fill=tk.X)

tk.Label(bill_frame, text="Product Name", font=global_font).grid(row=0, column=0, padx=(40,0))
product_bill_entry = tk.Entry(bill_frame, font=global_font)
product_bill_entry.grid(row=0, column=1, padx=(0,455))
product_bill_entry.focus()

bill_tree = ttk.Treeview(bill_frame, columns=("Name", "Qty", "Price", "Total"), show="headings",height=20)
for col, width in zip(("Name", "Qty", "Price", "Total"), (180, 80, 100, 120)):
    bill_tree.heading(col, text=col)
    bill_tree.column(col, width=width, anchor="center")
bill_tree.grid(row=1, column=0, columnspan=4, sticky="nsew")

bill_frame.grid_rowconfigure(1, weight=1)
bill_frame.grid_columnconfigure(0, weight=1)

total_label = tk.Label(bill_frame, text="Grand Total: 0.0", font=("Arial", 16))
total_label.grid(row=2, column=0, columnspan=4, pady=5)

# ---------------- Helpers ----------------
def format_qty_display(qty):
    # Show integer without .0, otherwise show up to 2 decimals (trim trailing zeros)
    try:
        if isinstance(qty, int):
            return str(qty)
        q = float(qty)
        if q.is_integer():
            return str(int(q))
        # remove trailing zeros but keep up to 2 decimals
        return f"{round(q,2):.2f}".rstrip('0').rstrip('.') if round(q,2) % 1 != 0 else str(int(round(q,2)))
    except:
        return str(qty)

def format_price(p):
    try:
        return f"{float(p):.2f}"
    except:
        return str(p)

# ---------------- Billing Functions ----------------
def refresh_bill():
    bill_tree.delete(*bill_tree.get_children())
    total = 0.0
    all_items = list(bill_items.items())

    for pid, item in all_items:
        name_en, price, qty = item
        line_total = math.ceil(price * qty)
        total += line_total

        display_qty = format_qty_display(qty)
        display_price = format_price(price)
        display_line = f"{line_total:,}"

        bill_tree.insert("", tk.END, iid=pid, values=(name_en, display_qty, display_price, display_line))

    total_label.config(text=f"Grand Total: {int(round(total)):,}")

    # --- AUTO SCROLL TO LAST ITEM ---
    if bill_items:
        last_item = list(bill_items.keys())[-1]
        bill_tree.see(last_item)

# ---------------- Inline Editing ----------------
editing_entry = None

def start_edit_cell(item, col_index):
    global editing_entry

    if editing_entry:
        try:
            editing_entry.destroy()
        except:
            pass
        editing_entry = None

    col_id = f"#{col_index+1}"
    try:
        x, y, width, height = bill_tree.bbox(item, col_id)
    except Exception:
        return
    if width <= 0:
        return

    cur_val = bill_tree.set(item, bill_tree["columns"][col_index])
    editing_entry = tk.Entry(bill_tree, font=global_font)
    editing_entry.insert(0, cur_val)
    editing_entry.place(x=x+2, y=y+2, width=width-4, height=height-4)
    editing_entry.focus()
    editing_entry.select_range(0, tk.END)

    def save_and_next(event=None, _item=item, _col=col_index):
        global editing_entry
        new_val = editing_entry.get().strip()
        try:
            pid = int(_item)
            if _col == 1:  # Qty column
                # allow ints or floats; store as int when integer else float rounded to 2 decimals
                val = float(new_val)
                new_qty = int(val) if float(val).is_integer() else round(val, 2)
                bill_items[pid][2] = max(0.01, new_qty)
            elif _col == 2:  # Price column
                new_price = round(float(new_val), 2)
                bill_items[pid][1] = max(0.0, new_price)
        except Exception:
            pass
        try:
            editing_entry.destroy()
        except:
            pass
        editing_entry = None
        refresh_bill()

        if _col == 1:
            root.after(50, lambda: start_edit_cell(_item, 2))
        else:
            root.after(50, lambda: product_bill_entry.focus())

    editing_entry.bind("<Return>", save_and_next)
    editing_entry.bind("<Escape>", lambda e: (editing_entry.destroy(), setattr(globals(), 'editing_entry', None)))

def on_tree_double_click(event):
    region = bill_tree.identify("region", event.x, event.y)
    if region != "cell":
        return
    item = bill_tree.identify_row(event.y)
    col = bill_tree.identify_column(event.x)
    if not item:
        return
    col_num = int(col.replace("#", "")) - 1
    if col_num in (1, 2):  # Qty or Price
        start_edit_cell(item, col_num)

bill_tree.bind("<Double-1>", on_tree_double_click)

# ---------------- Add to bill modified ----------------
def add_to_bill(event=None):
    name_en = product_bill_entry.get().strip()
    if not name_en:
        return
    cursor.execute("SELECT id, name_en, price FROM products WHERE LOWER(name_en)=LOWER(%s)", (name_en,))
    product = cursor.fetchone()
    if not product:
        messagebox.showerror("Error", "Product not found")
        product_bill_entry.delete(0, tk.END)
        return

    product_id, name_en, price = product
    price = float(price)
    if product_id in bill_items:
        # increment by 1 (keep type consistent: int -> int, float -> float)
        current = bill_items[product_id][2]
        if isinstance(current, int):
            bill_items[product_id][2] = current + 1
        else:
            bill_items[product_id][2] = round(current + 1, 2)
    else:
        bill_items[product_id] = [name_en, price, 1]

    refresh_bill()
    product_bill_entry.delete(0, tk.END)
    # After adding, focus Qty for editing
    root.after(50, lambda: start_edit_cell(product_id, 1))

def clear_bill():
    global editing_entry
    bill_items.clear()
    if editing_entry:
        editing_entry.destroy()
    refresh_bill()
    product_bill_entry.focus()

def delete_selected_bill_item(event=None):
    selected = bill_tree.selection()
    for iid in selected:
        if int(iid) in bill_items:
            del bill_items[int(iid)]
    refresh_bill()

def update_bill_suggestions(event=None):
    if event and event.keysym in ("Up", "Down", "Return"):
        return
    typed = product_bill_entry.get().strip().lower()

    # --- update suggestion box ---
    suggestion_box.delete(0, tk.END)
    cursor.execute("SELECT name_en FROM products")
    all_names = [row[0] for row in cursor.fetchall()]
    matches = all_names if not typed else [n for n in all_names if typed in n.lower()]
    for name in matches:
        suggestion_box.insert(tk.END, name)

    cursor.execute("SELECT id, name_en, name_hi, price FROM products ORDER BY name_en ASC")
    all_rows = cursor.fetchall()

    product_tree.delete(*product_tree.get_children())  # clear treeview

    if typed:
        filtered = [row for row in all_rows if typed in row[1].lower()]  # match Name_EN
    else:
        filtered = all_rows

    for row in filtered:
        product_tree.insert("", tk.END, values=row)

def on_product_entry_key(event):
    if event.keysym in ("Down","Up"):
        if suggestion_box.size()==0: return
        current = suggestion_box.curselection()
        if not current:
            index = 0 if event.keysym=="Down" else suggestion_box.size()-1
        else:
            index = current[0] + (1 if event.keysym=="Down" else -1)
            index %= suggestion_box.size()
        suggestion_box.selection_clear(0, tk.END)
        suggestion_box.selection_set(index)
        suggestion_box.activate(index)
        suggestion_box.see(index)
    elif event.keysym=="Return":
        if suggestion_box.curselection():
            selected = suggestion_box.get(suggestion_box.curselection())
            product_bill_entry.delete(0, tk.END)
            product_bill_entry.insert(0, selected)
        add_to_bill()

def delete_selected_bill_item(event=None):
    selected = bill_tree.selection()
    if not selected:
        return
    for iid in selected:
        product_id = int(iid)
        if product_id in bill_items:
            del bill_items[product_id]
    refresh_bill()
bill_tree.bind("<Delete>", delete_selected_bill_item)

def select_bill_suggestion(event):
    if suggestion_box.curselection():
        selected = suggestion_box.get(suggestion_box.curselection())
        product_bill_entry.delete(0, tk.END)
        product_bill_entry.insert(0, selected)
        suggestion_box.delete(0, tk.END)
        product_bill_entry.focus()

product_bill_entry.bind("<KeyRelease>", update_bill_suggestions)
product_bill_entry.bind("<Key>", on_product_entry_key)
suggestion_box.bind("<<ListboxSelect>>", select_bill_suggestion)

# ---------------- Print Bill (English Direct) ----------------
def print_bill():
    def do_print():
        try:
            p = Serial(devfile='COM30', baudrate=9600, timeout=1)
            font_p = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
            p._raw(b'\x1B\x37\x08\xF0\x02')

            img_width = 576
            line_height = 40
            x_name, x_qty, x_price, x_total = 10, 320, 390, 480

            total = 0.0
            height = (len(bill_items)+7) * line_height
            img = Image.new("L", (img_width, height), color=255)
            draw = ImageDraw.Draw(img)
            y = 0

            draw.text((150, y), "    ***** ESTIMATE *****", font=font_p, fill=0)
            y += line_height
            draw.text((x_name, y), "Item", font=font_p, fill=0)
            draw.text((x_qty, y), "Qty", font=font_p, fill=0)
            draw.text((x_price, y), "Price", font=font_p, fill=0)
            draw.text((x_total, y), "Total", font=font_p, fill=0)
            y += line_height

            for pid, item in bill_items.items():
                # use English name now
                cursor.execute("SELECT name_en FROM products WHERE id=%s", (pid,))
                result = cursor.fetchone()
                name_en = result[0] if result else "Unknown"

                _, price, qty = item
                line_total = math.ceil(price * qty)
                total += line_total
                display_qty = format_qty_display(qty)
                display_price = format_price(price)
                display_line = f"{line_total:,}"

                draw.text((x_name, y), name_en[:18], font=font_p, fill=0)
                draw.text((x_qty, y), display_qty, font=font_p, fill=0)
                draw.text((x_price, y), display_price, font=font_p, fill=0)
                draw.text((x_total, y), display_line, font=font_p, fill=0)
                y += line_height

            draw.text((0, y), "----------------------------------------------------------------------", font=font_p, fill=0)
            y += line_height
            draw.text((10, y), f"Items:  {len(bill_items)}                                Grand Total:    {int(round(total)):,}", font=font_p, fill=0)
            y += line_height
            draw.text((0, y), "----------------------------------------------------------------------", font=font_p, fill=0)
            y += line_height
            current_time = datetime.now().strftime("%d-%m-%Y  %I:%M %p")
            draw.text((10, y), f"Thank You!                            {current_time}", font=font_p, fill=0)
            y += line_height
            draw.text((100, y), "  - Developed By Nayan Parihar -", font=font_p, fill=0)

            bw_img = img.point(lambda x: 0 if x < 128 else 255, '1')
            p._raw(b'\x1B\x33\x08')
            p.image(bw_img)
            p.cut()

        except Exception as e:
            messagebox.showerror("Print Error", str(e))

    threading.Thread(target=do_print, daemon=True).start()

# ---------------- Buttons ----------------
tk.Button(bill_frame, text="Clear Bill", font=global_font, width=20, command=clear_bill).grid(row=3, column=0, padx=(0,20))
tk.Button(bill_frame, text="Print Bill", font=global_font, width=20, command=print_bill).grid(row=3, column=3)
# ---------------- Run ----------------
update_bill_suggestions()
root.mainloop()