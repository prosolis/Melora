import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MATRIX_HOMESERVER_URL: str = os.environ["MATRIX_HOMESERVER_URL"]
    MATRIX_BOT_USER_ID: str = os.environ["MATRIX_BOT_USER_ID"]
    MATRIX_BOT_ACCESS_TOKEN: str = os.environ["MATRIX_BOT_ACCESS_TOKEN"]
    MATRIX_ARRIVALS_ROOM_ID: str = os.environ["MATRIX_ARRIVALS_ROOM_ID"]

    WEBHOOK_SECRET: str = os.environ["WEBHOOK_SECRET"]

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "melora.db")


config = Config()
