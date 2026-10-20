from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.routes.triage import router as triage_router

load_dotenv()

app = FastAPI(title="Support Ticket Triage API")


@app.exception_handler(RequestValidationError)
async def input_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first_err = errors[0]
        loc = first_err.get("loc", [])
        field_name = loc[-1] if len(loc) > 1 else "body"
        msg = first_err.get("msg", "Invalid input")
    else:
        field_name = "body"
        msg = "Invalid input"

    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "field": str(field_name),
            "message": f"Invalid field '{field_name}': {msg}",
        },
    )


app.include_router(triage_router)
