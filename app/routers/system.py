from fastapi import APIRouter, status


system_router = APIRouter(prefix="/system")


@system_router.get("/healthcheck", status_code=status.HTTP_200_OK)
async def healthcheck():
    """
    Healthcheck endpoint.

    ### Response
    * {"msg": "ok"}
    """
    return {"msg": "ok"}
