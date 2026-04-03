from fastapi import APIRouter, Depends
from app.api.v1.endpoints.auth import (
    router as auth_router,
    require_auth,
    require_employee,
    require_management,
)
from app.api.v1.endpoints.analyze import router as analyze_router
from app.api.v1.endpoints.advisor import router as advisor_router
from app.api.v1.endpoints.leadership_trust import router as leadership_trust_router
from app.api.v1.endpoints.psychological_safety import router as psychological_safety_router
from app.api.v1.endpoints.workload_sustainability import router as workload_sustainability_router
from app.api.v1.endpoints.role_clarity import router as role_clarity_router
from app.api.v1.endpoints.decision_autonomy import router as decision_autonomy_router
from app.api.v1.endpoints.feedback_quality import router as feedback_quality_router
from app.api.v1.endpoints.recognition_fairness import router as recognition_fairness_router
from app.api.v1.endpoints.change_stability import router as change_stability_router
from app.api.v1.endpoints.collaboration_health import router as collaboration_health_router
from app.api.v1.endpoints.strategy import router as strategy_router
from app.api.v1.endpoints.dimension_state import router as dimension_state_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.employee_checkin import router as employee_checkin_router
from app.api.v1.endpoints.health import router as health_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)

# /v1/analyze
router.include_router(analyze_router, dependencies=[Depends(require_auth)])

# /v1/advisor
router.include_router(advisor_router, dependencies=[Depends(require_management)])

# NEW leadership trust advisory
router.include_router(leadership_trust_router, dependencies=[Depends(require_management)])
router.include_router(psychological_safety_router, dependencies=[Depends(require_management)])
router.include_router(workload_sustainability_router, dependencies=[Depends(require_management)])
router.include_router(role_clarity_router, dependencies=[Depends(require_management)])
router.include_router(decision_autonomy_router, dependencies=[Depends(require_management)])
router.include_router(feedback_quality_router, dependencies=[Depends(require_management)])
router.include_router(recognition_fairness_router, dependencies=[Depends(require_management)])
router.include_router(change_stability_router, dependencies=[Depends(require_management)])
router.include_router(collaboration_health_router, dependencies=[Depends(require_management)])
router.include_router(strategy_router, dependencies=[Depends(require_management)])
router.include_router(dimension_state_router, dependencies=[Depends(require_management)])
router.include_router(chat_router, dependencies=[Depends(require_management)])
router.include_router(employee_checkin_router, dependencies=[Depends(require_employee)])
