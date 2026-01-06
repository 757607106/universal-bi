from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import datasource, dataset, chat, dashboard
from app.core.config import settings
from app.db.session import engine
from app.models import metadata

# Create tables
metadata.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasource.router, prefix=f"{settings.API_V1_STR}/datasources", tags=["datasources"])
app.include_router(dataset.router, prefix=f"{settings.API_V1_STR}/datasets", tags=["datasets"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboards", tags=["dashboards"])

@app.get("/")
def root():
    return {"message": "Welcome to Universal BI API"}
