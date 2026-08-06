from fastapi import HTTPException


def field_error(status_code: int, field: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=[{"loc": ["body", field], "type": code}],
    )
