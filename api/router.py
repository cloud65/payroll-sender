from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, File, Request, Response
from fastapi.responses import PlainTextResponse, RedirectResponse

from service.parser import ServiceParser
from service.sender import ServiceSender

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/clear")
async def clear_cookies(request: Request, parser: ServiceParser):
    await parser.clear(dir=True)
    response = RedirectResponse(url="/")
    for cookie_name in request.cookies.keys():
        response.delete_cookie(key=cookie_name)

    return response


@router.get("/reload")
async def reload(parser: ServiceParser):
    if not parser.guid:
        return []
    return await parser.reports()


@router.post("/upload", response_model_exclude_unset=True)
async def upload_file(
    report: Annotated[Optional[bytes], File()],
    employees: Annotated[Optional[bytes], File()],
    parser: ServiceParser,
    response: Response,
):
    await parser.create_session(report, employees)
    parser.set_cookie(response)
    return await parser.reports()


@router.get(
    "/report/{guid}",
    response_class=PlainTextResponse,
)
async def get_reports(
    guid: UUID,
    parser: ServiceParser,
):
    return await parser.get_report(guid)


@router.post("/send")
async def send_reports(items: List[UUID], sender: ServiceSender):
    await sender.send(items)
    return {"status": True}
