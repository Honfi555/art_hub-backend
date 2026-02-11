from logging import Logger

from fastapi import APIRouter, HTTPException, Header, status
from fastapi.responses import JSONResponse
from psycopg2 import errors
from psycopg2.errorcodes import UNIQUE_VIOLATION

from ..logger import configure_logs
from ..utils import create_jwt, verify_jwt
from ..models.authorization import SignInData, ChangePasswordData
from ..database.users.users import process_user, check_credentials, check_login, change_password
from ..database.exceptions.change_password import IncorrectLoginException, OldPasswordMismatchException, \
	SamePasswordException

__all__: list[str] = ["authorization_router"]
authorization_router: APIRouter = APIRouter(
	prefix="/auth",
	tags=["Маршруты для действий с аккаунтом пользователя."]
)
logger: Logger = configure_logs(__name__)


@authorization_router.post("/sign_in")
async def sign_in_route(data: SignInData):
	logger.info(data.login)
	if not check_login(data.login):
		raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь с таким логином не найден")
	if not check_credentials(data.login, data.password):
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Введён неверный пароль")
	return JSONResponse(content={"success": True, "message": "Аутентификация пользователя прошла успешно",
								 "token": create_jwt(data.login)},
						status_code=status.HTTP_200_OK)


@authorization_router.post("/sign_up")
async def sign_up_route(data: SignInData):
	try:
		process_user(user={"login": data.login, "password": data.password, "description": ""})
		return JSONResponse(content={"success": True, "message": "Пользователь успешно зарегистрирован",
									 "token": create_jwt(data.login)},
							status_code=status.HTTP_201_CREATED)
	except errors.lookup(UNIQUE_VIOLATION):
		raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким логином уже существует")
	except Exception as e:
		logger.exception("Возникла непредвиденная ошибка при регистрации пользователя с логином %s. Ошибка: %s",
						 data.login, e)
		raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
							"Возникла непредвиденная ошибка на стороне сервера")


@authorization_router.post("/change_password")
@verify_jwt
async def change_password_route(data: ChangePasswordData, authorization: str = Header(...)):
	try:
		if change_password(data.login, data.old_password, data.new_password):
			return JSONResponse(content={"success": True, "message": "Пароль успешно сменён"},
								status_code=status.HTTP_200_OK)
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
							detail="Непредвиденная ошибка, на стороне сервера")
	except (IncorrectLoginException, OldPasswordMismatchException) as e:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
	except SamePasswordException as e:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
