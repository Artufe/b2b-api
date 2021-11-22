import json
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlmodel import Session
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.models import (
    Image,
    ImageRead,
    ImageTemplate,
    SingleImageGenerate,
)
import base64

router = APIRouter(
    prefix="/images",
    tags=["Images"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)

SUCCESS_MESSAGE = f"Image has been submitted for generation. " \
                  "Please allow up to a minute for it to be processed. " \
                  "It will appear in your image list when done."


def get_image_template(session, user_id, template_id):
    return session.query(ImageTemplate).where(ImageTemplate.user_id == user_id,
                                              ImageTemplate.image_template_id == template_id).first()


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(*,
                    session: Session = Depends(get_session),
                    user: UserDB = Depends(current_active_user),
                    image_id: int
                    ):
    global SUCCESS_MESSAGE

    image = session.query(Image).where(Image.user_id == user.id,
                                       Image.image_id == image_id).first()
    b64_image = base64.b64encode(image.image).decode('ascii')
    b64_thumbnail = base64.b64encode(image.thumbnail).decode('ascii')

    if image.image_format.lower() == "jpg":
        data_format = "jpeg"
    else:
        data_format = image.image_format.lower()

    image.image = f"data:image/{data_format};base64,{b64_image}"
    image.thumbnail = f"data:image/{data_format};base64,{b64_thumbnail}"

    if not image:
        raise HTTPException(status_code=404, detail="Image Template not found")

    return image


@router.post("/generate_single_image")
async def single_image_generate(*,
                                session: Session = Depends(get_session),
                                user: UserDB = Depends(current_active_user),
                                parameters: SingleImageGenerate
                                ):
    global SUCCESS_MESSAGE

    image_template = get_image_template(session, user.id, parameters.image_template_id)
    if not image_template:
        raise HTTPException(status_code=404, detail="Image Template not found")

    # Build dict with all the info required for the Image generation consumer
    image_template = image_template.dict()
    image_template["base_image"] = base64.b64encode(image_template["base_image"]).decode('ascii')
    message_body = {
        "template": image_template,
        "parameters": parameters.dict()
    }
    message_body = json.dumps(message_body, default=str)

    rmq, rmqc = rmq_init()
    rmqc.basic_publish(exchange='B2B', routing_key='image_generation', body=message_body)
    rmq.close()

    return {"ok": True, "message": SUCCESS_MESSAGE}

# @router.post("/generate_query_images")
# async def query_images_generate(*,
#                                 session: Session = Depends(get_session),
#                                 user: UserDB = Depends(current_active_user),
#                                 parameters: QueryImageGenerate
#                                 ):
#     global SUCCESS_MESSAGE
#
#     image_template = get_image_template(session, user.id, parameters.image_template_id)
#     if not image_template:
#         raise HTTPException(status_code=404, detail="Image Template not found")
#     query = session.query(ImageTemplate).where(ImageTemplate.user_id == user_id,
#                                               ImageTemplate.image_template_id == template_id).first()
#
#     # Build dict with all the info required for the Image generation consumer
#     image_template = image_template.dict()
#     image_template["base_image"] = base64.b64encode(image_template["base_image"]).decode('ascii')
#     message_body = {
#         "template": image_template,
#         "parameters": parameters.dict()
#     }
#     message_body = json.dumps(message_body, default=str)
#
#     rmq, rmqc = rmq_init()
#     rmqc.basic_publish(exchange='B2B', routing_key='image_generation', body=message_body)
#
#     return {"ok": True, "message": SUCCESS_MESSAGE}
