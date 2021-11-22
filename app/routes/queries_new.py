import json

import pika
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlmodel import Session
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.dependencies import rmq_init

from app.models import (
    Query,
    QueryRead,
)

router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.post("/new/location")
async def launch_location_query(*,
                                user: UserDB = Depends(current_active_user),
                                rmq: pika.connection.Connection = Depends(rmq_init),
                                sector: str,
                                location: str,
                                project_id: int,
                                params: Optional[dict] = None
                                ):
    # Validate the parameters to not contain special characters
    if not sector.isalnum() or not location.isalnum():
        raise HTTPException(status_code=403, detail="Query contains invalid characters.")
    # Any validation for user query count should be done at this point
    # That way if user has exceeded or matched theyr query limit
    # the query does not get through to the RMQ queue

    # Setup pika connection and declare all needed exchanges/queues
    rmqc = rmq.channel()
    rmqc.exchange_declare(exchange='B2B', durable=True)
    rmqc.queue_declare(queue="new_queries")
    rmqc.queue_bind(exchange='B2B', queue='new_queries')

    params = {"sector": sector, "location": location}
    message_body = json.dumps(
        {"query_type": "location",
         "user_id": str(user.id),
         "project_id": project_id,
         "params": params,
         }
    )
    rmqc.basic_publish(exchange='B2B', routing_key='new_queries', body=message_body)
    rmq.close()

    return {"ok": True}
