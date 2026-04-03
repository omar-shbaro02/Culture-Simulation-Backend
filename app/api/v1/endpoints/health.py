from fastapi import APIRouter, Response, status

router = APIRouter(tags=["Health"])


@router.head("/health", status_code=status.HTTP_200_OK)
def health_check():
    return Response(status_code=status.HTTP_200_OK)
