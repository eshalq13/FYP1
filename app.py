import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# STYLE + CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="NEXORA | Modern Clothing Store",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.getenv("STORE_DB_PATH", "nexora_store.db")
ADMIN_PASSWORD = os.getenv("STORE_ADMIN_PASSWORD", "admin12345")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family: 'DM Sans', sans-serif;}
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px;}
.hero {padding: 3rem 2.5rem; border-radius: 22px; color: white;
       background: linear-gradient(115deg,#111827 0%,#334155 60%,#64748b 100%);}
.hero h1 {font-size: clamp(2rem,5vw,4rem); line-height:1.05; font-weight:800; margin:0;}
.hero p {font-size:1.05rem; color:#e2e8f0; margin-top:1rem;}
.product-card {border:1px solid #e5e7eb; border-radius:16px; padding:12px; height:100%;}
.product-card img {width:100%; height:240px; object-fit:cover; border-radius:11px;}
.muted {color:#64748b; font-size:.9rem;}
.metric-card {padding:18px; border:1px solid #e5e7eb; border-radius:15px;}
div.stButton > button {border-radius:10px; font-weight:600;}
[data-testid="stSidebar"] {border-right:1px solid #e5e7eb;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL,
            compare_price REAL DEFAULT 0,
            image TEXT DEFAULT '',
            sizes TEXT DEFAULT 'S,M,L,XL',
            colors TEXT DEFAULT 'Black,White',
            stock INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'New',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            size TEXT NOT NULL,
            color TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        """)

        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            sample = [
                ("Essential Oversized Tee", "Men", "A relaxed everyday cotton t-shirt.", 2490, 2990,
                 "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=900", "S,M,L,XL", "Black,White,Olive", 30),
                ("Classic Hoodie", "Men", "Soft fleece hoodie for cooler days.", 5490, 6490,
                 "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=900", "S,M,L,XL", "Black,Grey,Cream", 18),
                ("Everyday Denim", "Women", "Straight-fit denim with a timeless finish.", 5990, 6990,
                 "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=900", "XS,S,M,L", "Blue,Black", 14),
                ("Minimal Summer Dress", "Women", "Lightweight dress for everyday comfort.", 4790, 0,
                 "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=900", "XS,S,M,L", "Black,Cream", 12),
                ("Urban Sneakers", "Accessories", "Clean low-top sneakers for daily wear.", 7990, 8990,
                 "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=900", "39,40,41,42,43", "Red,White,Black", 10),
                ("Canvas Tote Bag", "Accessories", "A simple carry-all canvas tote.", 1990, 0,
                 "https://images.unsplash.com/photo-1544816155-12df9643f363?w=900", "One Size", "Natural,Black", 25),
            ]
            con.executemany("""
                INSERT INTO products
                (name,category,description,price,compare_price,image,sizes,colors,stock,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, [(*p, datetime.now().isoformat(timespec="seconds")) for p in sample])


def money(value):
    return f"PKR {float(value):,.0f}"


def get_products(include_inactive=False):
    with db() as con:
        query = "SELECT * FROM products"
        if not include_inactive:
            query += " WHERE active=1"
        query += " ORDER BY id DESC"
        return pd.read_sql_query(query, con)


def get_cart():
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    return st.session_state.cart


def cart_total():
    cart = get_cart()
    total = 0.0
    with db() as con:
        for key, qty in cart.items():
            pid = int(key.split("|")[0])
            row = con.execute("SELECT price FROM products WHERE id=? AND active=1", (pid,)).fetchone()
            if row:
                total += row["price"] * qty
    return total


def add_to_cart(product_id, size, color, quantity=1):
    key = f"{product_id}|{size}|{color}"
    cart = get_cart()
    cart[key] = cart.get(key, 0) + quantity
    st.session_state.cart = cart


def place_order(customer, cart):
    if not cart:
        raise ValueError("Your cart is empty.")
    with db() as con:
        lines = []
        total = 0.0
        for key, qty in cart.items():
            pid, size, color = key.split("|", 2)
            product = con.execute(
                "SELECT * FROM products WHERE id=? AND active=1", (int(pid),)
            ).fetchone()
            if not product:
                raise ValueError("A product in your cart is no longer available.")
            if qty <= 0 or product["stock"] < qty:
                raise ValueError(f"Not enough stock for {product['name']}. Available: {product['stock']}.")
            lines.append((product, size, color, qty))
            total += product["price"] * qty

        now = datetime.now().isoformat(timespec="seconds")
        cur = con.execute("""
            INSERT INTO orders
            (customer_name,email,phone,address,city,total,status,created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (customer["name"], customer["email"], customer["phone"],
              customer["address"], customer["city"], total, "New", now))
        order_id = cur.lastrowid

        for product, size, color, qty in lines:
            con.execute("""
                INSERT INTO order_items
                (order_id,product_id,product_name,size,color,quantity,unit_price)
                VALUES (?,?,?,?,?,?,?)
            """, (order_id, product["id"], product["name"], size, color, qty, product["price"]))
            con.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, product["id"]))
    return order_id, total


# ------------------------------------------------------------
# CUSTOMER STORE
# ------------------------------------------------------------
def storefront():
    st.markdown("""
    <div class="hero">
      <div style="letter-spacing:4px;font-weight:700;color:#cbd5e1;">N E X O R A</div>
      <h1>Wear your<br>own story.</h1>
      <p>Everyday essentials. Thoughtful details. Made for your style.</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    products = get_products()
    if products.empty:
        st.info("No products are available right now.")
        return

    categories = ["All"] + sorted(products["category"].dropna().unique().tolist())
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("Search products", placeholder="Try hoodie, denim, t-shirt...")
    with c2:
        category = st.selectbox("Category", categories)
    with c3:
        sort_by = st.selectbox("Sort by", ["Featured", "Price: low to high", "Price: high to low"])

    filtered = products.copy()
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    if search:
        filtered = filtered[filtered["name"].str.contains(search, case=False, na=False) |
                            filtered["description"].str.contains(search, case=False, na=False)]
    if sort_by == "Price: low to high":
        filtered = filtered.sort_values("price")
    elif sort_by == "Price: high to low":
        filtered = filtered.sort_values("price", ascending=False)

    st.markdown("## Shop the collection")
    st.caption(f"{len(filtered)} products")
    if filtered.empty:
        st.warning("No products match your search.")
        return

    cols = st.columns(3)
    for index, (_, p) in enumerate(filtered.iterrows()):
        with cols[index % 3]:
            with st.container(border=True):
                if p["image"]:
                    st.image(p["image"], use_container_width=True)
                st.markdown(f"**{p['name']}**")
                st.caption(p["category"])
                if p["compare_price"] and p["compare_price"] > p["price"]:
                    st.markdown(f"**{money(p['price'])}**  ~~{money(p['compare_price'])}~~")
                else:
                    st.markdown(f"**{money(p['price'])}**")
                st.caption(p["description"])
                st.caption(f"{int(p['stock'])} in stock" if p["stock"] > 0 else "Out of stock")

                sizes = [x.strip() for x in str(p["sizes"]).split(",") if x.strip()]
                colors = [x.strip() for x in str(p["colors"]).split(",") if x.strip()]
                if p["stock"] > 0 and sizes and colors:
                    size = st.selectbox("Size", sizes, key=f"size_{p['id']}")
                    color = st.selectbox("Color", colors, key=f"color_{p['id']}")
                    qty = st.number_input("Qty", min_value=1, max_value=max(1, int(p["stock"])),
                                          value=1, step=1, key=f"qty_{p['id']}")
                    if st.button("Add to cart", key=f"add_{p['id']}", use_container_width=True):
                        add_to_cart(int(p["id"]), size, color, int(qty))
                        st.toast(f"{p['name']} added to cart")
                else:
                    st.button("Unavailable", disabled=True, key=f"unavailable_{p['id']}",
                              use_container_width=True)


def cart_page():
    st.title("Your shopping cart")
    cart = get_cart()
    if not cart:
        st.info("Your cart is empty. Add something you love from the store.")
        return

    rows = []
    with db() as con:
        for key, qty in list(cart.items()):
            pid, size, color = key.split("|", 2)
            p = con.execute("SELECT * FROM products WHERE id=?", (int(pid),)).fetchone()
            if p:
                rows.append({"key": key, "name": p["name"], "size": size, "color": color,
                             "price": p["price"], "stock": p["stock"], "qty": qty,
                             "subtotal": p["price"] * qty})
    for item in rows:
        a, b, c, d = st.columns([3, 1, 1, 1])
        a.markdown(f"**{item['name']}**  \nSize: {item['size']} · Color: {item['color']}")
        b.write(money(item["price"]))
        new_qty = c.number_input("Qty", min_value=1, max_value=max(1, int(item["stock"])),
                                 value=min(item["qty"], max(1, int(item["stock"]))),
                                 key=f"cartqty_{item['key']}")
        if new_qty != item["qty"]:
            cart[item["key"]] = int(new_qty)
            st.session_state.cart = cart
        if d.button("Remove", key=f"remove_{item['key']}"):
            cart.pop(item["key"], None)
            st.session_state.cart = cart
            st.rerun()
        st.divider()

    total = cart_total()
    st.subheader(f"Total: {money(total)}")
    st.caption("Shipping charges, if any, can be added to this checkout flow later.")
    st.markdown("### Checkout")
    with st.form("checkout_form"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        phone = st.text_input("Phone number")
        address = st.text_area("Delivery address")
        city = st.text_input("City")
        submitted = st.form_submit_button("Place order", type="primary", use_container_width=True)
    if submitted:
        if not all([name.strip(), email.strip(), phone.strip(), address.strip(), city.strip()]):
            st.error("Please complete all checkout fields.")
        elif "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            try:
                order_id, paid = place_order(
                    {"name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                     "address": address.strip(), "city": city.strip()}, cart
                )
                st.session_state.cart = {}
                st.success(f"Order #{order_id} placed successfully. Total: {money(paid)}")
                st.balloons()
            except (ValueError, sqlite3.Error) as exc:
                st.error(str(exc))


# ------------------------------------------------------------
# ADMIN
# ------------------------------------------------------------
def admin_login():
    st.title("Admin sign in")
    st.caption("Store management is restricted to authorized administrators.")
    with st.form("admin_login"):
        password = st.text_input("Admin password", type="password")
        submit = st.form_submit_button("Sign in", type="primary")
    if submit:
        if password == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")


def admin_dashboard():
    st.title("Store overview")
    st.caption("Live store data from the local database.")
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=15000, key="admin_refresh")
        st.caption("Dashboard refreshes every 15 seconds.")
    except ImportError:
        st.info("For automatic refresh, install streamlit-autorefresh: pip install streamlit-autorefresh")

    with db() as con:
        total_sales = con.execute(
            "SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='Cancelled'"
        ).fetchone()[0]
        order_count = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        new_orders = con.execute("SELECT COUNT(*) FROM orders WHERE status='New'").fetchone()[0]
        product_count = con.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        stock_count = con.execute("SELECT COALESCE(SUM(stock),0) FROM products WHERE active=1").fetchone()[0]
        low_stock = con.execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock<=5").fetchone()[0]
        sales_df = pd.read_sql_query("""
            SELECT date(created_at) AS day, SUM(total) AS revenue
            FROM orders WHERE status!='Cancelled'
            GROUP BY date(created_at) ORDER BY day
        """, con)
        recent = pd.read_sql_query("""
            SELECT id,customer_name,total,status,created_at
            FROM orders ORDER BY id DESC LIMIT 8
        """, con)

    m = st.columns(5)
    metrics = [
        ("Revenue", money(total_sales)),
        ("Orders", f"{order_count:,}"),
        ("New orders", f"{new_orders:,}"),
        ("Active products", f"{product_count:,}"),
        ("Units in stock", f"{stock_count:,}"),
    ]
    for col, (label, value) in zip(m, metrics):
        col.metric(label, value)
    if low_stock:
        st.warning(f"{low_stock} product(s) have 5 or fewer units remaining.")

    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Revenue over time")
        if not sales_df.empty:
            sales_df["day"] = pd.to_datetime(sales_df["day"])
            st.line_chart(sales_df.set_index("day")["revenue"])
        else:
            st.info("Sales will appear here after the first order.")
    with right:
        st.subheader("Recent orders")
        if recent.empty:
            st.info("No orders yet.")
        else:
            for _, order in recent.iterrows():
                st.markdown(
                    f"**Order #{order['id']} · {order['customer_name']}**  \n"
                    f"{money(order['total'])} · {order['status']}  \n"
                    f"<span class='muted'>{order['created_at']}</span>",
                    unsafe_allow_html=True
                )
                st.divider()


def admin_inventory():
    st.title("Inventory management")
    products = get_products(include_inactive=True)
    if not products.empty:
        view = products[["id", "name", "category", "price", "stock", "active"]].copy()
        view["active"] = view["active"].map({1: "Yes", 0: "No"})
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Add a product")
    with st.form("add_product", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Product name")
        category = c2.selectbox("Category", ["Men", "Women", "Accessories"])
        description = st.text_area("Description")
        c3, c4, c5 = st.columns(3)
        price = c3.number_input("Selling price (PKR)", min_value=0.0, value=2500.0, step=100.0)
        compare_price = c4.number_input("Original price (PKR)", min_value=0.0, value=0.0, step=100.0)
        stock = c5.number_input("Opening stock", min_value=0, value=10, step=1)
        image_url = st.text_input("Product image URL")
        sizes = st.text_input("Sizes (comma separated)", "S,M,L,XL")
        colors = st.text_input("Colors (comma separated)", "Black,White")
        add = st.form_submit_button("Add product", type="primary")
    if add:
        if not name.strip() or price <= 0:
            st.error("Product name and a price greater than zero are required.")
        else:
            with db() as con:
                con.execute("""
                    INSERT INTO products
                    (name,category,description,price,compare_price,image,sizes,colors,stock,active,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,1,?)
                """, (name.strip(), category, description, price, compare_price, image_url.strip(),
                      sizes, colors, int(stock), datetime.now().isoformat(timespec="seconds")))
            st.success("Product added.")
            st.rerun()

    st.subheader("Update or remove a product")
    active_products = products[products["active"] == 1] if not products.empty else products
    if not active_products.empty:
        selected = st.selectbox("Choose product", active_products["id"].tolist(),
                                format_func=lambda pid: f"#{pid} — {active_products.loc[active_products.id == pid, 'name'].iloc[0]}")
        product = active_products[active_products["id"] == selected].iloc[0]
        with st.form(f"edit_product_{selected}"):
            new_name = st.text_input("Name", product["name"])
            new_price = st.number_input("Price (PKR)", min_value=0.0, value=float(product["price"]))
            new_stock = st.number_input("Stock quantity", min_value=0, value=int(product["stock"]))
            new_category = st.selectbox("Category", ["Men", "Women", "Accessories"],
                                        index=["Men", "Women", "Accessories"].index(product["category"])
                                        if product["category"] in ["Men", "Women", "Accessories"] else 0)
            save = st.form_submit_button("Save changes")
        if save:
            with db() as con:
                con.execute("UPDATE products SET name=?,price=?,stock=?,category=? WHERE id=?",
                            (new_name.strip(), new_price, int(new_stock), new_category, int(selected)))
            st.success("Product updated.")
            st.rerun()
        if st.button("Deactivate product", type="secondary"):
            with db() as con:
                con.execute("UPDATE products SET active=0 WHERE id=?", (int(selected),))
            st.success("Product deactivated.")
            st.rerun()


def admin_orders():
    st.title("Orders and sales")
    with db() as con:
        orders = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", con)
    if orders.empty:
        st.info("No orders have been placed yet.")
        return
    st.dataframe(orders, use_container_width=True, hide_index=True)
    selected = st.selectbox("Select order", orders["id"].tolist(),
                            format_func=lambda oid: f"Order #{oid} — {orders.loc[orders.id == oid, 'customer_name'].iloc[0]}")
    with db() as con:
        items = pd.read_sql_query("""
            SELECT product_id,product_name,size,color,quantity,unit_price,
                   quantity*unit_price AS subtotal
            FROM order_items WHERE order_id=?
        """, con, params=(int(selected),))
        order = con.execute("SELECT status FROM orders WHERE id=?", (int(selected),)).fetchone()
    st.subheader(f"Order #{selected} details")
    st.dataframe(items, use_container_width=True, hide_index=True)
    statuses = ["New", "Processing", "Shipped", "Delivered", "Cancelled"]
    current_status = order["status"]
    new_status = st.selectbox("Order status", statuses, index=statuses.index(current_status),
                              disabled=(current_status == "Cancelled"))
    if current_status == "Cancelled":
        st.caption("Cancelled orders cannot be reopened in this demo, to avoid inventory errors.")
    if st.button("Update order status", type="primary", disabled=(current_status == "Cancelled")):
        if new_status == "Cancelled" and current_status != "Cancelled":
            with db() as con:
                con.execute("UPDATE orders SET status=? WHERE id=?", (new_status, int(selected)))
                for _, item in items.iterrows():
                    # Restore stock only once when an order is first cancelled.
                    con.execute("UPDATE products SET stock=stock+? WHERE id=?",
                                (int(item["quantity"]), int(item["product_id"])))
        else:
            with db() as con:
                con.execute("UPDATE orders SET status=? WHERE id=?", (new_status, int(selected)))
        st.success("Order status updated.")
        st.rerun()


# ------------------------------------------------------------
# APP ROUTER
# ------------------------------------------------------------
init_db()

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

st.sidebar.markdown("## NEXORA")
st.sidebar.caption("Modern clothing store")
page = st.sidebar.radio("Navigation", ["Shop", "Shopping cart", "Admin dashboard"])

if page == "Shop":
    storefront()
elif page == "Shopping cart":
    cart_page()
else:
    if not st.session_state.admin_authenticated:
        admin_login()
    else:
        st.sidebar.success("Admin authenticated")
        admin_page = st.sidebar.radio("Admin menu", ["Overview", "Inventory", "Orders"])
        if st.sidebar.button("Log out"):
            st.session_state.admin_authenticated = False
            st.rerun()
        if admin_page == "Overview":
            admin_dashboard()
        elif admin_page == "Inventory":
            admin_inventory()
        else:
            admin_orders()

st.sidebar.divider()
st.sidebar.caption("NEXORA Store · Demo application")
