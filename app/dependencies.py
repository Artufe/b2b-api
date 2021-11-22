import os
import pika

from sqlmodel import (
    create_engine,
    Session,
)

#
# DB
#
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")

# Gets DB password from docker secret
with open("/run/secrets/b2b_db_pass") as f:
    DB_PASS = f.read().strip()

DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DB_URL
)


def get_session():
    with Session(engine) as session:
        yield session


def rmq_init():
    # RabbitMQ connection open
    # Connect with pika to RabbitMQ in localhost
    rmq = pika.BlockingConnection(pika.URLParameters('amqp://arthur:FlaskTubCupp@host.docker.internal:5672/%2F'))
    return rmq


