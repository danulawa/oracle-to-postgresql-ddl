from flask import Flask, render_template, request, send_file
from io import BytesIO
import re
import csv

app = Flask(__name__)

# Load the Oracle to PostgreSQL data type mapping
def load_data_type_mapping(file_path):
    mapping = {}
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            mapping[row['Oracle_Data_Type'].strip().lower()] = row['PostgreSQL_Data_Type'].strip().lower()
    return mapping

# Convert Oracle DDL to PostgreSQL DDL
def convert_oracle_to_postgresql(oracle_ddl, type_mapping):
    # Extract schema and table name
    schema_table_pattern = r'CREATE TABLE \"(.*?)\"\.\"(.*?)\"'
    match = re.search(schema_table_pattern, oracle_ddl)
    schema_name, table_name = match.groups()
    schema_name = schema_name.lower()
    table_name = table_name.lower()

    # Extract columns and their types
    column_pattern = r'\s*\"(.*?)\"\s+(.*?)(?:,|\))'
    columns = re.findall(column_pattern, oracle_ddl)

    # Extract primary key
    primary_key_pattern = r'PRIMARY KEY \((.*?)\)'
    primary_key_match = re.search(primary_key_pattern, oracle_ddl)
    primary_key_columns = primary_key_match.group(1).replace('"', '').split(',') if primary_key_match else []

    # Convert columns to PostgreSQL format
    converted_columns = []
    for col_name, col_type in columns:
        col_name = col_name.lower()
        col_type = col_type.lower()

        # Map Oracle data type to PostgreSQL data type
        for oracle_type, pg_type in type_mapping.items():
            if col_type.startswith(oracle_type):
                col_type = pg_type
                break

        converted_columns.append(f"{col_name} {col_type}")

    # Create the PostgreSQL DDL
    create_table_ddl = f"CREATE TABLE {schema_name}.{table_name} (\n    "
    create_table_ddl += ",\n    ".join(converted_columns)
    create_table_ddl += "\n);"

    # Add the primary key constraint
    primary_key_ddl = ""
    if primary_key_columns:
        primary_key_ddl = (
            f"ALTER TABLE {schema_name}.{table_name} "
            f"ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ({', '.join(primary_key_columns)});"
        )

    return create_table_ddl, primary_key_ddl

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    oracle_ddl = request.form['oracle_ddl']  # Input from textarea
    type_mapping = load_data_type_mapping("data_type_conversion.csv")

    # Convert Oracle DDL to PostgreSQL DDL
    create_table_ddl, primary_key_ddl = convert_oracle_to_postgresql(oracle_ddl, type_mapping)

    # Save the PostgreSQL DDL content to a BytesIO buffer
    output_file = BytesIO()
    output_file.write((create_table_ddl + "\n" + primary_key_ddl).encode())
    output_file.seek(0)  # Move to the beginning of the buffer

    # Send the file for download
    return send_file(output_file, as_attachment=True, download_name="postgresql_ddl.txt", mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)
