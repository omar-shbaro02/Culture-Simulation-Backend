from fastapi import APIRouter, HTTPException, Response, status

from db.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check_get():
    return {"status": "ok"}


@router.head("/health", status_code=status.HTTP_200_OK)
def health_check():
    return Response(status_code=status.HTTP_200_OK)


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_check_db():
    try:
        await check_db_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return {"status": "ok", "database": "connected"}
