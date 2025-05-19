import pyodbc

def connect_db(server=None, database=None, username=None, password=None):
    if server and database and username and password:
        # Home.py will pass arguments → use them
        connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={server};"
            f"Database={database};"
            f"Uid={username};"
            f"Pwd={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=60;"
        )
    else:
        # Default for other pages
        connection_string = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=mptcecommerce-sql-server.database.windows.net;"
            "Database=mptcecommerce-db;"
            "Uid=mptcadmin;"
            "Pwd=Mptc@2025;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=60;"
        )

    return pyodbc.connect(connection_string)
