from typing import Optional
from logging import Logger

from fastapi import APIRouter, Body, Header, Query, status, HTTPException
from fastapi.responses import JSONResponse

from ..logger import configure_logs
from ..utils import verify_jwt, get_jwt_login
from ..models.articles import ArticleAnnouncement, ArticleData, ArticleFull, ImagesAdd, ArticleAdd
from ..database.utils import check_article_owner
from ..database.articles.articles import (select_articles_announcement, select_article, select_article_full,
										  insert_article,
										  update_article, delete_article, select_articles_by_search)
from app.database.articles.images import delete_images, insert_images

__all__: list[str] = ["feed_router"]
feed_router: APIRouter = APIRouter(
	prefix="/feed",
	tags=["Маршруты для получения статей пользователей"]
)
logger: Logger = configure_logs(__name__)


@feed_router.get("/articles")
@verify_jwt
async def get_articles_route(authorization: str = Header(...),
							 amount: Optional[int] = 10,
							 chunk: Optional[int] = 1,
							 login: Optional[str] = None):
	try:
		articles_data: list[ArticleAnnouncement] = select_articles_announcement(amount, chunk, login)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "articles": articles_data})
	except Exception as e:
		logger.error("An error excepted in articles route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.get("/article")
@verify_jwt
async def get_article_route(article_id: int, authorization: str = Header(...)):
	try:
		article_data: ArticleData = select_article(article_id)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "article": article_data})
	except Exception as e:
		logger.error("An error excepted in arctile route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.get("/article_full")
@verify_jwt
async def get_article_route(article_id: int, authorization: str = Header(...)):
	try:
		article_data: ArticleFull = select_article_full(article_id)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "article": article_data})
	except Exception as e:
		logger.error("An error excepted in article_full route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.delete("/remove_images")
@verify_jwt
async def remove_article_images_route(
		article_id: int = Query(..., description="ID статьи"),
		image_ids: list[str] = Body(..., description="Список ID изображений для удаления"),
		authorization: str = Header(...)
):
	try:
		check_article_owner(article_id, get_jwt_login(authorization))
		deleted = delete_images(article_id, image_ids)
		return JSONResponse(
			status_code=status.HTTP_200_OK,
			content={"success": True, "deleted_image_ids": deleted}
		)
	except Exception as e:
		logger.error("An error excepted in remove_images route, error: %s", str(e))
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=str(e)
		)


@feed_router.put("/add_images")
@verify_jwt
async def add_article_images_route(
		article_id: int = Query(..., description="ID статьи"),
		images: list[str] = Body(..., description="Список base64-строк или URL файлов для вставки"),
		authorization: str = Header(...)
):
	try:
		check_article_owner(article_id, get_jwt_login(authorization))
		created: list[str] = insert_images(ImagesAdd(article_id=article_id, images=images))
		return JSONResponse(
			status_code=status.HTTP_201_CREATED,
			content={"success": True, "created_image_ids": created}
		)
	except Exception as e:
		logger.error("An error excepted in add_images route, error: %s", str(e))
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=str(e)
		)


@feed_router.post("/add_article")
@verify_jwt
async def add_article_route(article_data: ArticleAdd, authorization: str = Header(...)):
	try:
		article_id: int = insert_article(
			ArticleFull(id=0,
						title=article_data.title,
						user_name=get_jwt_login(authorization),
						announcement=article_data.announcement,
						article_body=article_data.article_body)
		)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "article_id": article_id})
	except Exception as e:
		logger.error("An error excepted in add_article route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.put("/update_article")
@verify_jwt
async def update_article_route(article_data: ArticleFull, authorization: str = Header(...)):
	try:
		check_article_owner(article_data.id, get_jwt_login(authorization))
		update_article(article_data)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
	except Exception as e:
		logger.error("An error excepted in update_article route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.delete("/remove_article")
@verify_jwt
async def remove_article_route(article_id: int, authorization: str = Header(...)):
	try:
		check_article_owner(article_id, get_jwt_login(authorization))
		delete_article(article_id)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True})
	except Exception as e:
		logger.error("An error excepted in remove_article route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@feed_router.get("/search_articles")
@verify_jwt
async def search_articles_route(query: str, amount: Optional[int] = 5, chunk: Optional[int] = 1,
								login: Optional[str] = None, authorization: str = Header(...)):
	try:
		result: list[dict] = select_articles_by_search(query_str=query, amount=amount, chunk=chunk, login=login)
		return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "results": result})
	except Exception as e:
		logger.error("An error excepted in search_articles route, error: %s", str(e))
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
