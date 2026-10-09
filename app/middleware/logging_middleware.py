"""Structured request logging: request id, method, path, status, duration."""
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.configuration.constants import REQUEST_ID_HEADER

logger = logging.getLogger("walletledger.request")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            logger.info(json.dumps({
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,  # path only: never log headers/tokens/body
                "status": status,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }))
