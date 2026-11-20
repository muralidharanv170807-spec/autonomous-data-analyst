import os
import re
import duckdb
import pandas as pd


class DuckDBEngine:
    def __init__(self, csv_directory: str = "data"):
        self.csv_directory = csv_directory
        self._conn = duckdb.connect(database=":memory:")
        self._load_csv_files()

    def _load_csv_files(self) -> None:
        if not os.path.exists(self.csv_directory):
            return
        for filename in sorted(os.listdir(self.csv_directory)):
            if filename.lower().endswith(".csv"):
                table_name = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(filename)[0]).lower()
                if table_name and table_name[0].isdigit():
                    table_name = f"t_{table_name}"
                filepath = os.path.join(self.csv_directory, filename)
                clean_path = filepath.replace("\\", "/")
                try:
                    self._conn.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{clean_path}', ignore_errors=true, null_padding=true, strict_mode=false)"
                    )
                except Exception:
                    try:
                        df = pd.read_csv(filepath, encoding="utf-8-sig", on_bad_lines="skip")
                        self._conn.register("_tmp_df", df)
                        self._conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM _tmp_df")
                        self._conn.unregister("_tmp_df")
                    except Exception:
                        pass

    def drop_table_for_file(self, filename: str) -> None:
        table_name = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(filename)[0]).lower()
        if table_name and table_name[0].isdigit():
            table_name = f"t_{table_name}"
        if table_name:
            self._conn.execute(f"DROP TABLE IF EXISTS {table_name}")

    def get_schema(self) -> str:
        tables = [row[0] for row in self._conn.execute("SHOW TABLES").fetchall()]
        if not tables:
            return "No tables loaded."
        schema_lines = []
        for table in tables:
            cols = self._conn.execute(f"DESCRIBE {table}").fetchall()
            col_defs = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
            schema_lines.append(f"Table '{table}': {col_defs}")
        return "\n".join(schema_lines)

    def execute_query(self, sql: str) -> dict:
        cleaned = sql.strip().rstrip(";")
        first_token = cleaned.split()[0].upper() if cleaned else ""
        if first_token not in ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN"):
            raise ValueError("Only read-only SELECT queries are permitted.")
        rel = self._conn.execute(cleaned)
        columns = [desc[0] for desc in rel.description] if rel.description else []
        rows = rel.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        return {"columns": columns, "data": data, "row_count": len(data)}
