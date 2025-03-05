import sqlite3
import pandas as pd

# Load the data from CSV file
<<<<<<< HEAD
df = pd.read_csv('ea.csv', low_memory=False)
=======
df = pd.read_csv('farmers.csv', low_memory=False)
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e

# Data Clean Up
df.columns = df.columns.str.strip()

# Create a connection tot the SQLite database
conn = sqlite3.connect('db.sqlite3')

# Load the data from csv file to sqlite database

<<<<<<< HEAD
df.to_sql('dashboard_extensionagentdata', conn, if_exists='append')
=======
df.to_sql('dashboard_farmers', conn, if_exists='append')
>>>>>>> 84788627ce78f3da16ca57cf61180eb67855d59e

#close the connection
conn.close()