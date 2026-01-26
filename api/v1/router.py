from fastapi import APIRouter
from app.api.v1.endpoints.analyze import router as analyze_router
from app.api.v1.endpoints.advisor import router as advisor_router

router = APIRouter()

router.include_router(analyze_router)
router.include_router(advisor_router)
