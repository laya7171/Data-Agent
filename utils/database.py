import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv


class DatabaseUtil:

    def __init__(self):
        load_dotenv()

        # Project root: Data Agent/
        base_dir = Path(__file__).resolve().parent.parent

        # .env should contain: DB_PATH=data/agent.db
        db_path = base_dir / os.getenv("DB_PATH", "data/agent.db")

        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.execute("PRAGMA foreign_keys = ON")

            print(f"Connected to database: {db_path}")

        except sqlite3.Error as e:
            raise RuntimeError(
                f"Error connecting to database: {e}"
            ) from e

    def schema_details(self):
        """
        Return all SQLite tables, columns, data types,
        and up to five sample rows from each table.
        """

        schema_info_context = "Database Schema: SQLite\n"

        cursor = self.connection.cursor()

        try:
            # SQLite stores table information in sqlite_master
            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name;
            """)

            tables_list = cursor.fetchall()

            for (table_name,) in tables_list:

                schema_info_context += (
                    f"\nTable: {table_name}\n"
                )

                # Get column names and data types
                cursor.execute(
                    f'PRAGMA table_info("{table_name}")'
                )

                columns_list = cursor.fetchall()

                for column in columns_list:
                    # PRAGMA table_info format:
                    # cid, name, type, notnull, default_value, pk
                    column_name = column[1]
                    data_type = column[2] or "UNKNOWN"

                    schema_info_context += (
                        f"  Column: {column_name}, "
                        f"Data Type: {data_type}\n"
                    )

                # Get sample data
                cursor.execute(
                    f'SELECT * FROM "{table_name}" LIMIT 5'
                )

                sample_data = cursor.fetchall()

                schema_info_context += "  Sample Data:\n"

                for row in sample_data:
                    schema_info_context += f"    {row}\n"

        except sqlite3.Error as e:
            error_message = f"Error fetching schema details: {e}"
            print(error_message)
            schema_info_context = error_message

        finally:
            cursor.close()

        return schema_info_context

    def execute_sql(self, query):
        """
        Execute a SQL query and return the result as a string.
        """

        cursor = self.connection.cursor()

        try:
            cursor.execute(query)

            # SELECT queries return rows
            if cursor.description is not None:
                result = cursor.fetchall()
            else:
                # INSERT, UPDATE, DELETE, etc.
                self.connection.commit()
                result = {
                    "status": "success",
                    "rows_affected": cursor.rowcount
                }

            return str(result)

        except sqlite3.Error as e:
            self.connection.rollback()
            print(f"Error executing query: {e}")
            return None

        finally:
            cursor.close()

    def close(self):
        """Close the SQLite connection."""
        if self.connection:
            self.connection.close()
            print("SQLite connection closed.")


