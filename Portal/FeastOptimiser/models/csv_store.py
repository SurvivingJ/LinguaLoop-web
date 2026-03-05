import csv
import os
from filelock import FileLock


class CSVStore:
    """Central CSV-based data persistence layer.

    All data is stored as CSV files in a single directory.
    JSON fields are stored as JSON strings in CSV columns.
    List fields are stored as pipe-delimited strings.
    Dates are ISO strings. Booleans are "True"/"False".
    """

    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, table_name):
        return os.path.join(self.data_dir, f"{table_name}.csv")

    def _lock(self, table_name):
        return FileLock(self._path(table_name) + ".lock")

    def read_all(self, table_name):
        """Read all rows from a CSV file. Returns list[dict]."""
        path = self._path(table_name)
        if not os.path.exists(path):
            return []
        with self._lock(table_name):
            with open(path, 'r', newline='', encoding='utf-8') as f:
                return list(csv.DictReader(f))

    def write_all(self, table_name, rows, fieldnames=None):
        """Overwrite entire CSV file with rows."""
        path = self._path(table_name)
        if not rows:
            # Write empty file with headers if fieldnames provided
            if fieldnames:
                with self._lock(table_name):
                    with open(path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
            return
        if not fieldnames:
            fieldnames = list(rows[0].keys())
        with self._lock(table_name):
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    def append_row(self, table_name, row):
        """Append a single row. Creates file with headers if it doesn't exist."""
        path = self._path(table_name)
        with self._lock(table_name):
            file_exists = os.path.exists(path) and os.path.getsize(path) > 0
            with open(path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

    def query(self, table_name, **filters):
        """Filter rows by exact string match on fields. Returns list[dict]."""
        rows = self.read_all(table_name)
        for key, value in filters.items():
            rows = [r for r in rows if r.get(key) == str(value)]
        return rows

    def upsert(self, table_name, row, key_field='id'):
        """Insert or update a row by key_field."""
        rows = self.read_all(table_name)
        key_val = str(row[key_field])
        serialized = {k: str(v) for k, v in row.items()}
        updated = False
        for i, r in enumerate(rows):
            if r.get(key_field) == key_val:
                # Preserve field order from existing row, add new fields
                merged = dict(r)
                merged.update(serialized)
                rows[i] = merged
                updated = True
                break
        if not updated:
            rows.append(serialized)
        self.write_all(table_name, rows)
        return serialized

    def delete(self, table_name, **filters):
        """Delete rows matching ALL filters. Returns count deleted."""
        rows = self.read_all(table_name)
        original_count = len(rows)
        remaining = []
        for r in rows:
            match = all(r.get(k) == str(v) for k, v in filters.items())
            if not match:
                remaining.append(r)
        if remaining:
            self.write_all(table_name, remaining)
        elif rows:
            # All rows deleted — write empty file with headers
            self.write_all(table_name, [], fieldnames=list(rows[0].keys()))
        return original_count - len(remaining)

    def next_id(self, table_name):
        """Generate next integer ID for auto-increment tables."""
        rows = self.read_all(table_name)
        if not rows:
            return 1
        ids = []
        for r in rows:
            try:
                ids.append(int(r.get('id', 0)))
            except (ValueError, TypeError):
                continue
        return max(ids, default=0) + 1
