import streamlit_authenticator as stauth

# Hashed password for: adminpass123 (you can change)
hashed_passwords = stauth.Hasher(['Mptc@2025']).generate()

credentials = {
    "usernames": {
        "mptcadmin": {
            "name": "MPTC Admin User",
            "password": hashed_passwords[0],
        }
    }
}
