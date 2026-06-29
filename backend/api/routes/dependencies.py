"""放路由层共用的辅助函数。"""

from fastapi.responses import JSONResponse
from backend.api.dto.schemas import ApiError, ErrorResponse


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """生成统一格式的错误响应（JSONResponse）。

    当系统出错或者输入参数不对时，用它可以保证返回给前端的错误格式是一致的，方便前端解析。
    """
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ApiError(
                code=code,
                message=message,
            )
        ).model_dump(),
    )
