import psycopg
from scraper.config import settings

def get_connection():
    # psycopg 3 can connect using the postgres:// URL directly
    return psycopg.connect(settings.database_url)
