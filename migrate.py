# Models...
from models.User import User
from models.APIKey import APIKey

print("Starting migration script...")

# User table
if User.exists():
    print("User table already exists, not running migrations")
    # Uncomment below if you wish to delete and re-create the table, to reset your data on purpose
    # User.delete_table()
    # User.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
else:
    print("User table does not exist, creating it now...")
    User.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


# APIKey table
if APIKey.exists():
    print("APIKey table already exists, not running migrations")
    # Uncomment below if you wish to delete and re-create the table, to reset your data on purpose
    # APIKey.delete_table()
    # APIKey.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
else:
    print("APIKey table does not exist, creating it now...")
    APIKey.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
