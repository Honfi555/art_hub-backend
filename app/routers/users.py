from logging import Logger

from fastapi import APIRouter, Header, status, HTTPException
from fastapi.responses import JSONResponse

from ..logger import configure_logs
from ..utils import verify_jwt, get_jwt_login
from ..models.users import AuthorInfo, DescriptionUpdate
from ..database.users.users import select_user_info, change_description

__all__: list[str] = ["users_router"]
users_router: APIRouter = APIRouter(
	prefix="/users",
	tags=["Маршруты для получения информации о пользователях"]
)
logger: Logger = configure_logs(__name__)


@users_router.get("/author")
@verify_jwt
async def get_author_route(author_name: str, authorization: str = Header(...)):
	try:
		author_info: AuthorInfo = select_user_info(username=author_name)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "author_info": author_info})
	except Exception as e:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@users_router.post("/update_description")
@verify_jwt
async def update_description_route(data: DescriptionUpdate, authorization: str = Header(...)):
	try:
		login: str = get_jwt_login(authorization)
		change_description(login, data.description)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
	except Exception as e:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
