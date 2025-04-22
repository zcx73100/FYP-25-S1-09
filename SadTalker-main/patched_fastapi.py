from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class PatchedFastAPI(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Override the handler for request validation errors
        @self.exception_handler(RequestValidationError)
        async def safe_validation_handler(request: Request, exc: RequestValidationError):
            print("⚠️ Custom validation error caught")

            try:
                safe_errors = []
                for err in exc.errors():
                    safe_err = {}
                    for k, v in err.items():
                        # Safely handle bytes that would otherwise crash FastAPI
                        if isinstance(v, bytes):
                            safe_err[k] = repr(v[:100])  # convert to safe preview
                        else:
                            safe_err[k] = v
                    safe_errors.append(safe_err)

                return JSONResponse(status_code=400, content={"detail": safe_errors})
            except Exception as e:
                print("❌ Failed to handle validation error safely:", repr(e))
                return JSONResponse(
                    status_code=500,
                    content={"detail": "Internal error while handling validation failure."}
                )
