# utils/auth_utils.py
import streamlit as st
import streamlit_authenticator as stauth
from auth_config import credentials

def run_auth():
    authenticator = stauth.Authenticate(
        credentials,
        "mptc_app_cookie",
        "mptc_app_key",
        cookie_expiry_days=0.1251
    )
    name, auth_status, username = authenticator.login(fields={"Form name": "Login"}, location="main")

    if auth_status is False:
        st.error("Incorrect username or password")

    if auth_status is None:
        st.warning("Please enter your username and password")
        st.stop()

    authenticator.logout("Logout", "sidebar")
    return name, username
