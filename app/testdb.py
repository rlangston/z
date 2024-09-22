import sqlite3

def fetch_records(db_name, table_name):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)

    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Query to fetch all records from the given table
    query = f"SELECT * FROM {table_name};"

    try:
        # Execute the query
        cursor.execute(query)

        # Fetch all the records
        records = cursor.fetchall()

        # Check if records are found
        if records:
            # Get column names
            column_names = [description[0] for description in cursor.description]
            print(" | ".join(column_names))
            print("-" * (len(column_names) * 15))

            # Display each record
            for record in records:
                print(" | ".join(map(str, record)))
        else:
            print(f"No records found in table '{table_name}'")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    # Close the connection
    conn.close()

if __name__ == "__main__":
    # Example: Provide your database name and table name here
    database_name = 'z.db'   # Replace with your database name
    table_name = 'zettels'       # Replace with your table name

    # Fetch and display records
    fetch_records(database_name, table_name)
