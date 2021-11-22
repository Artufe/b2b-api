import json
from typing import (
    List,
)

import pika.connection
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    Form
)
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.models import (
    Image,
    ImageTemplate,
    ImageTemplateRead,
)
from app.dependencies import rmq_init
import base64

router = APIRouter(
    prefix="/image-templates",
    tags=["Image Templates"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.post("/new", response_model=ImageTemplateRead)
async def create_image_template(*,
                                session: Session = Depends(get_session),
                                user: UserDB = Depends(current_active_user),
                                rmq: pika.connection.Connection = Depends(rmq_init),
                                image_template: str = Form(...),
                                base_image: UploadFile = File(...)
                                ):
    # Verify that the uploaded base image is of correct format (PNG or JPG)
    img_format = base_image.filename.split(".")[-1].lower()
    if img_format not in ["jpg", "png", "jpeg"]:
        raise HTTPException(
            status_code=422,
            detail=f"Image must be of .png or .jpg format. You uploaded a {img_format} format image, which is not supported. Please upload a compatible image to create the template."
        )

    image_template = ImageTemplate.parse_raw(image_template)
    image_template.user_id = user.id
    image_template.base_image = await base_image.read()
    image_template.base_image_format = img_format
    session.add(image_template)
    try:
        session.commit()
    except IntegrityError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error.__cause__).replace("\n", " ").strip()
        ) from error
    session.refresh(image_template)

    # Generate a preview image.
    # This will make a entry in the images table
    # Which means the first image for each template is always a preview.
    image_template.base_image = base64.b64encode(image_template.base_image).decode('ascii')
    message_body = {
        "template": image_template.dict()
    }
    message_body = json.dumps(message_body, default=str)

    rmqc = rmq.channel()
    rmqc.exchange_declare(exchange='B2B', durable=True)
    rmqc.queue_declare(queue='image_generation')
    rmqc.queue_bind(exchange='B2B', queue='image_generation')

    rmqc.basic_publish(exchange='B2B', routing_key='image_generation', body=message_body)
    rmq.close()
    return image_template


@router.get("/", response_model=List[ImageTemplateRead])
async def get_all_image_templates(*,
                                  session: Session = Depends(get_session),
                                  user: UserDB = Depends(current_active_user),
                                  offset: int = 0,
                                  limit: int = Query(default=100, lte=100),
                                  include_thumbnail: bool
                                  ):
    query = session.query(ImageTemplate).where(ImageTemplate.user_id == user.id)
    results = query.offset(offset).limit(limit).all()
    templates = []
    for template in results:
        if include_thumbnail:
            image = session.query(Image).where(Image.user_id == user.id,
                                               Image.template_id == template.image_template_id,
                                               Image.preview == True).first()
            if image:
                b64_thumbnail = base64.b64encode(image.thumbnail).decode('ascii')
                if template.base_image_format.lower() == "jpg":
                    data_format = "jpeg"
                else:
                    data_format = template.base_image_format.lower()

                thumbnail = f"data:image/{data_format};base64,{b64_thumbnail}"
                thumbnail_id = image.image_id

        if not include_thumbnail or not image:
            thumbnail = None
            thumbnail_id = None

        images_generated = session.query(Image).where(
            Image.template_id == template.image_template_id,
            Image.preview == False
        ).count()

        templates.append(ImageTemplateRead(**template.dict(),
                                           thumbnail=thumbnail, thumbnail_id=thumbnail_id,
                                           images_generated=images_generated))

    return templates


@router.get("/{image_template_id}", response_model=ImageTemplateRead)
async def get_image_template(*,
                             session: Session = Depends(get_session),
                             user: UserDB = Depends(current_active_user),
                             image_template_id: int,
                             include_thumbnail: bool
                             ):
    image_template = session.query(ImageTemplate).where(ImageTemplate.user_id == user.id,
                                                        ImageTemplate.image_template_id == image_template_id).first()
    if not image_template:
        raise HTTPException(status_code=404, detail="Image template not found")
    if include_thumbnail:
        image = session.query(Image).where(Image.user_id == user.id,
                                           Image.template_id == image_template_id,
                                           Image.preview == True).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image template preview not found")
        b64_thumbnail = base64.b64encode(image.thumbnail).decode('ascii')
        if image_template.base_image_format.lower() == "jpg":
            data_format = "jpeg"
        else:
            data_format = image_template.base_image_format.lower()

        thumbnail = f"data:image/{data_format};base64,{b64_thumbnail}"
        image_template = ImageTemplateRead(**image_template.dict(), thumbnail=thumbnail, thumbnail_id=image.image_id)

    images_generated = session.query(Image).where(
        Image.template_id == image_template.image_template_id,
        Image.preview == False
    ).count()

    image_template = image_template.dict()
    image_template["images_generated"] = images_generated
    return image_template



# @router.patch("/{campaign_format_id}", response_model=CampaignFormatRead)
# async def update_campaign_format(*,
#     session: Session = Depends(get_session),
#     campaign_format_id: int,
#     campaign_format: CampaignFormatUpdate
# ):
#     db_campaign_format = session.get(CampaignFormat, campaign_format_id)
#     if not db_campaign_format:
#         raise HTTPException(status_code=404, detail="Campaign format not found")
#     campaign_format_data = campaign_format.dict(exclude_unset=True)
#     for key, value in campaign_format_data.items():
#         setattr(db_campaign_format, key, value)
#     session.add(db_campaign_format)
#     try:
#         session.commit()
#     except IntegrityError as error:
#         raise HTTPException(
#             status_code=422,
#             detail=str(error.__cause__).replace("\n", " ").strip()
#         ) from error
#     session.refresh(db_campaign_format)
#     return db_campaign_format

@router.delete("/{image_template_id}")
async def delete_image_template(*,
                                session: Session = Depends(get_session),
                                user: UserDB = Depends(current_active_user),
                                image_template_id: int
                                ):
    image_template = session.query(ImageTemplate).where(ImageTemplate.user_id == user.id,
                                                        ImageTemplate.image_template_id == image_template_id).first()
    if not image_template:
        raise HTTPException(status_code=404, detail="Image Template not found")
    session.delete(image_template)
    try:
        session.commit()
    except IntegrityError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error.__cause__).replace("\n", " ").strip()
        ) from error
    return {"ok": True}
