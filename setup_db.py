from db.connection import DatabaseConnection
from db.schema import SchemaManager


def main():
    db = DatabaseConnection()
    schema = SchemaManager(db)

    print("Creating database tables...")
    schema.create_all_tables()

    print("Verifying created tables...")
    schema.verify_tables()

    print("Database setup complete. All tables are created and verified.")


if __name__ == "__main__":
    main()
