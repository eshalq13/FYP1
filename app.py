import streamlit as st
import sqlite3
import os

# ======================
# Database setup
# ======================
def init_db():
    conn = sqlite3.connect("shop.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            image TEXT
        )
    ''')
    # Insert demo products only once
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ("Headphones", 1200, "pictures/headphones.png"),
            ("Keyboard", 900, "pictures/keyboard.png"),
            ("Monitor", 3500, "pictures/monitor.png"),
            ("Mouse", 600, "pictures/mouse.png"),
        ]
        c.executemany("INSERT INTO products (name, price, image) VALUES (?, ?, ?)", products)
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect("shop.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()
    return rows

# ======================
# Streamlit App
# ======================
st.set_page_config(page_title="Virtual Store Demo", layout="wide")
st.title("🛍️ Virtual Store App")

# Initialize database
init_db()

# Shopping cart session state
if "cart" not in st.session_state:
    st.session_state["cart"] = []

menu = st.sidebar.radio("Menu", ["Products", "My Cart"])

if menu == "Products":
    products = get_products()
    cols = st.columns(2)
    for idx, product in enumerate(products):
        with cols[idx % 2]:
            # Show product image (if file exists)
            if os.path.exists(product[3]):
                st.image(product[3], width=150)
            else:
                st.warning("Image not found!")

            st.write(f"**{product[1]}**")
            st.write(f"💵 {product[2]} USD")
            if st.button("Add to Cart", key=f"add_{product[0]}"):
                st.session_state["cart"].append(product)
                st.success(f"{product[1]} added to cart!")

elif menu == "My Cart":
    st.header("🛒 Your Shopping Cart")
    cart = st.session_state["cart"]
    if not cart:
        st.info("Your cart is empty.")
    else:
        total = 0
        for item in cart:
            st.write(f"- {item[1]} — {item[2]} USD")
            total += item[2]
        st.subheader(f"Total: {total} USD")
        if st.button("Clear Cart"):
            st.session_state["cart"] = []
            st.success("Cart cleared!")
