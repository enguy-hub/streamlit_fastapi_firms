from fastapi import APIRouter

from models.firms_models import RequestFirmsDataURL
from services.firms_services import create_firms_csv_url


router = APIRouter(prefix="/create")


@router.post(
    "/firms_csv_url",
    description="Fetch FIRMS CSV Data URL based on inputed country code",
    status_code=201,
)
def get_firms_csv_url(input: RequestFirmsDataURL):
    return create_firms_csv_url(
        input.product,
        input.country,
        input.days_ago,
    )
