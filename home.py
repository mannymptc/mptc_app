import streamlit as st
import os
from utils.db import connect_db

st.set_page_config(page_title="🏠 MPTC Dashboard", layout="wide")

# ----------------------- HEADER LOGO & BRANDS -----------------------
col_logo, col_spacer, col_brands = st.columns([3, 0.05, 10])

with col_logo:
    st.image("assets/logo.png", width=250)

with col_spacer:
    st.markdown("<div style='border-left: 2px solid #cccccc; height: 50px;'></div>", unsafe_allow_html=True)

with col_brands:
    st.image("assets/brands.png", width=900)
    
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------------- PAGE TITLE -----------------------
st.markdown("<h1 style='text-align: center;'>🏭 Welcome to MPTC App</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------------- 3 COLUMN LAYOUT -----------------------
col1, col2, col3 = st.columns([1, 1.2, 1])

# ----------------------- COL 1: AZURE SQL TEST -----------------------
with col1:
    st.markdown("### 🔌 Azure DB Connection")

    with st.expander("🛠️ Connection Details", expanded=True):
        server = st.text_input("Server", value="mptcecommerce-sql-server.database.windows.net")
        db = st.text_input("Database", value="mptcecommerce-db")
        user = st.text_input("User", value="mptcadmin")
        pwd = st.text_input("Password", type="password", value="Mptc@2025")

        if st.button("✅ Test Connection"):
            conn = connect_db(server, db, user, pwd)
            if conn:
                st.success("✅ Azure SQL connection successful!")
                conn.close()
            else:
                st.error("❌ Connection failed. Please verify credentials.")

# ----------------------- COL 2: TASK LIST -----------------------
with col2:
    st.markdown("### 📋 Team Task List")

    with st.form("task_form"):
        task_input = st.text_input("Add a new task")
        submitted = st.form_submit_button("➕ Add Task")
        if submitted:
            if task_input.strip():
                with open("tasks.txt", "a") as f:
                    f.write(task_input + "\n")
                st.success("✅ Task added!")
    
    if os.path.exists("tasks.txt"):
        with open("tasks.txt") as f:
            tasks = [t.strip() for t in f.readlines()]
        if tasks:
            st.markdown("#### 🔖 Current Tasks")
            st.markdown("<ul style='padding-left: 20px;'>", unsafe_allow_html=True)
            for task in tasks:
                st.markdown(f"<li>{task}</li>", unsafe_allow_html=True)
            st.markdown("</ul>", unsafe_allow_html=True)
        else:
            st.info("📭 No tasks added yet.")
    else:
        st.info("📭 No tasks file found.")

# ----------------------- COL 3: GROUP CHAT -----------------------
with col3:
    st.markdown("### 💬 Team Group Chat")

    with st.form("chat_form"):
        chat = st.text_area("Type your message", height=100)
        send = st.form_submit_button("📨 Send")
        if send and chat.strip():
            with open("chat_data.txt", "a", encoding="utf-8") as f:
                f.write(chat.strip() + "\n")
            st.experimental_rerun()

    if os.path.exists("chat_data.txt"):
        with open("chat_data.txt", "r", encoding="utf-8") as f:
            messages = [msg.strip() for msg in f.readlines()]
        if messages:
            st.markdown("#### 📨 Recent Messages")
            for msg in messages[-30:]:
                st.markdown(f"- {msg}")
        else:
            st.info("💬 No messages yet.")
    else:
        st.info("💬 No chat history yet.")

# -------------------------------------
st.markdown("---")
st.markdown("👤 **Built by Mantavya Jain** ")

