import streamlit as st
import os
from utils.db import connect_db

st.set_page_config(page_title="🏠 MPTC Dashboard", layout="wide")

st.title("🏭 MPTC Home Page")

# ----------------------- LAYOUT: 3 COLUMNS -----------------------
col1, col2, col3 = st.columns([1, 1, 1])

# ----------------------- COL 1: Azure SQL -----------------------
with col1:
    st.markdown("### 🔌 Azure SQL Test")
    
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
            st.error("❌ Failed to connect.")

# ----------------------- COL 2: Task List -----------------------
with col2:
    st.markdown("### 📋 Team Task List")
    
    task_input = st.text_input("Add a new task")
    if st.button("Add Task"):
        if task_input.strip():
            with open("tasks.txt", "a") as f:
                f.write(task_input + "\n")
            st.success("Task added!")
    
    if os.path.exists("tasks.txt"):
        with open("tasks.txt") as f:
            tasks = f.readlines()
        st.markdown("#### 🔖 Current Tasks")
        for task in tasks:
            st.markdown(f"- {task.strip()}")
    else:
        st.info("No tasks yet.")

# ----------------------- COL 3: Group Chat -----------------------
with col3:
    st.markdown("### 💬 Group Chat")

    chat = st.text_area("Type your message", height=100)

    if st.button("Send"):
        if chat.strip() != "":
            with open("chat_data.txt", "a", encoding="utf-8") as f:
                f.write(chat + "\n")
            st.experimental_rerun()

    if os.path.exists("chat_data.txt"):
        st.markdown("#### 📨 Chat History")
        with open("chat_data.txt", "r", encoding="utf-8") as f:
            messages = f.readlines()
            for msg in messages[-50:]:
                st.markdown(f"- {msg.strip()}")
    else:
        st.info("No chat messages yet.")
