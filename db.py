import psycopg2


def get_connection():
    return psycopg2.connect(
        dbname="pizza",
        user="postgres",
        password="labs",
        host="localhost",
        port="5432",
    )