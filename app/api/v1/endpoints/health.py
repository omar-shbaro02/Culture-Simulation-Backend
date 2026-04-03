from fastapi import APIRouter, Response, status

router = APIRouter(tags=["Health"])


@router.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return Response(status_code=status.HTTP_200_OK)
