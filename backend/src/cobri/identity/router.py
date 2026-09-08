from typing import Annotated

from fastapi import APIRouter, Depends

from Cobri.backend.src.cobri.identity.auth import Principal, get_current_principal

router = APIRouter(prefix="/auth", tags=["identity"])


@router.get("/me", response_model=Principal)
async def current_identity(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    return principal
