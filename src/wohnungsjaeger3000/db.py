from sqlalchemy import create_engine, String, Table, Column, MetaData, select

# SQLite database file
engine = create_engine("sqlite:////app/output/seen.db")

metadata = MetaData()

seen_table = Table(
    "seen",
    metadata,
    Column("seen", String, primary_key=True),
)

# Creates the database/table if it does not already exist.
metadata.create_all(engine)

def add_to_seen(value: str) -> None:
    """Add a string to the database if it is not already present."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    with engine.begin() as connection:
        # SQLite-specific INSERT OR IGNORE behavior.
        connection.exec_driver_sql(
            "INSERT OR IGNORE INTO seen (seen) VALUES (?)",
            (value,),
        )


def already_seen(value: str) -> bool:
    """Return True if the string exists in the database."""
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    query = select(seen_table.c.seen).where(seen_table.c.seen == value)

    with engine.connect() as connection:
        return connection.execute(query).first() is not None