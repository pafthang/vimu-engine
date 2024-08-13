import hashlib
import json

from fastapi import APIRouter, Request

from config import settings
from engine import Engine, EngineException
from models.api import APIResponse
from models.engine import Data

router = APIRouter()
engine = Engine()


@router.post("/engine", response_model=APIResponse)
async def root(data: Data, request: Request) -> APIResponse:
    try:
        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()
        cached_data = await redis.get(request_hash) if redis is not None else None
        if cached_data is not None:
            processed_data = {
                'output': json.loads(cached_data),
                'plots': []
            }
        else:
            processed_data = engine.process(data)
            # we cannot cache figured_bass_realize because its outcome is non-deterministic
        return APIResponse(status="success", data=processed_data, error=None)
    except EngineException as e:
        return APIResponse(status="error", data=None, error={"message": str(e), "node": e.node})


