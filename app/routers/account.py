from fastapi import APIRouter, Depends, status

from app.clients.kucoin_api import APIClient
from app.utils.dependencies import get_kucoin_client


accounts_router = APIRouter(prefix="/accounts")


@accounts_router.get("/list", status_code=status.HTTP_200_OK)
async def get_accounts(
    client: APIClient = Depends(get_kucoin_client),
):
    """
    Get a list of accounts.
    """
    response = await client.get_accounts()
    return response.json()


@accounts_router.get("/orders", status_code=status.HTTP_200_OK, deprecated=True)
async def get_orders(
    client: APIClient = Depends(get_kucoin_client),
):
    """
    Request via this endpoint to get your current order list.
    """
    response = await client.get_orders()
    return response.json()
