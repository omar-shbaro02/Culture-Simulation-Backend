import os

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.api.v1.router import router
from app.services.auth_db import init_auth_db

app = FastAPI(title="Culture Simulation v2")

default_frontend_origins = ",".join(
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://culturesim.netlify.app",
        "https://culturesim.vaisolutions.ai",
    ]
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        default_frontend_origins,
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.head("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return Response(status_code=status.HTTP_200_OK)


app.include_router(router, prefix="/v1")


@app.on_event("startup")
async def startup():
    await init_auth_db()
