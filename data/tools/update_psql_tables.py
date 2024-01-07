"""
This script updates the record_maps and record_rename tables in psql
(Required to run the "best map of the year poll" script in /cogs/ddnet_map_awards.py)

Run convert_race_db.sh if you want to update the record_race table in psql (not needed for the mentioned script above)
"""

import psycopg2
import mysql.connector

maria_host =
maria_user =
maria_password =
maria_database =
maria_table_rename =
maria_table_maps =

pg_host =
pg_password =

maria_connection = mysql.connector.connect(
    host=maria_host,
    user=maria_user,
    password=maria_password,
    database=maria_database
)
maria_cursor = maria_connection.cursor()

psql_connection = psycopg2.connect(
    host=pg_host,
    password=pg_password,
)
psql_cursor = psql_connection.cursor()

maria_cursor.execute('SELECT * FROM {}'.format(maria_table_rename))
rename_rows = maria_cursor.fetchall()

for row in rename_rows:
    if row[3] is not None:
        timestamp_str = row[3].strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_str = None

    psql_cursor.execute(
        'SELECT * FROM record_rename WHERE oldname = %s AND name = %s',
        (row[0], row[1])
    )
    existing_row = psql_cursor.fetchone()

    if not existing_row:
        psql_cursor.execute(
            'INSERT INTO record_rename (oldname, name, renamedby, "Timestamp") VALUES (%s, %s, %s, %s)',
            (row[0], row[1], row[2], timestamp_str)
        )

maria_cursor.execute('SELECT * FROM {}'.format(maria_table_maps))
maps_rows = maria_cursor.fetchall()

for row in maps_rows:
    if row[5] is not None:
        timestamp_str = row[5].strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp_str = None

    psql_cursor.execute(
        'SELECT * FROM record_maps WHERE Map::bytea = %s AND Server::bytea = %s AND Points = %s AND Stars = %s AND Mapper::bytea = %s AND "Timestamp" = %s',
        (row[0], row[1], row[2], row[3], row[4], timestamp_str)
    )
    existing_row = psql_cursor.fetchone()

    if not existing_row:
        psql_cursor.execute(
            'INSERT INTO record_maps (Map, Server, Points, Stars, Mapper, "Timestamp") VALUES (%s, %s, %s, %s, %s, %s)',
            (row[0].decode('utf-8'), row[1].decode('utf-8'), row[2], row[3], row[4].decode('utf-8'), timestamp_str)
        )

psql_connection.commit()
maria_cursor.close()
psql_cursor.close()
maria_connection.close()
psql_connection.close()

print('Data copied successfully from MariaDB to PostgreSQL.')
