from typing import Optional
from logging import Logger

from sqlite3 import InterfaceError, OperationalError
from psycopg2.extras import RealDictCursor

from app.database.connect import connect_pg
from app.logger import configure_logs
from app.models.articles import ArticleData, ArticleAnnouncement, ArticleFull

__all__: list[str] = ["select_articles_announcement", "select_article", "select_article_full", "insert_article",
					  "update_article", "delete_article", "select_articles_by_search"]
logger: Logger = configure_logs(__name__)


def select_articles_announcement(amount: Optional[int] = None,
								 chunk: Optional[int] = None,
								 login: Optional[str] = None) -> list[ArticleAnnouncement]:
	logger.info("Начало получения статей из базы данных.")
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    SELECT art.article_id,
                           art.title,
                           us.login,
                           art.announcement
                    FROM articles.articles art
                             JOIN users.users us ON art.user_id = us.id
					"""
			params = []
			if login:
				query += "\nWHERE us.login = %s"
				params.append(login)
			query += "\nORDER BY art.article_id DESC"
			if amount and chunk:
				query += """\nOFFSET %s
						 \nLIMIT %s
						 """
				params.extend([(chunk - 1) * amount, amount])
			cur.execute(query, params)
			result = cur.fetchall()
			logger.info("Количество полученных статей %s", len(result))
			return result
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def select_article(article_id: int) -> ArticleData | None:
	logger.info("Начало получения статьи, c id %s", article_id)
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    SELECT art.article_id,
                           art.title,
                           us.login,
                           art.article_body
                    FROM articles.articles art
                             JOIN users.users us ON art.user_id = us.id
                    WHERE article_id = %s;
					"""
			cur.execute(query, (article_id,))
			result = cur.fetchone()
			logger.info("Получена статься с id %s", article_id)
			return result
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def select_article_full(article_id: int) -> ArticleFull | None:
	logger.info("Начало получения полной статьи, c id %s", article_id)
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    SELECT art.article_id,
                           art.title,
                           us.login,
                           art.announcement,
                           art.article_body
                    FROM articles.articles art
                             JOIN users.users us ON art.user_id = us.id
                    WHERE article_id = %s;
					"""
			cur.execute(query, (article_id,))
			result = cur.fetchone()
			logger.info("Получена полная статься, с id %s", article_id)
			return result
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def insert_article(article: ArticleFull) -> int | None:
	logger.info("Начало вставки статьи, с названием %s", article.title)
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    INSERT INTO articles.articles
                        (title, user_id, announcement, article_body)
                    VALUES (%s, (SELECT id FROM users.users WHERE login = %s), %s, %s)
                    RETURNING article_id;
					"""
			data = (article.title, article.user_name, article.announcement, article.article_body)
			cur.execute(query, data)
			result = cur.fetchone()[0]
			conn.commit()
			logger.info("Вставлена статься, с названием %s", article.title)
			return result
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def update_article(article: ArticleFull) -> None:
	logger.info("Начало обновления статьи, с id %s", article.id)
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    UPDATE articles.articles
                    SET title        = %s,
                        article_body = %s,
                        announcement = %s
                    WHERE article_id = %s;
					"""
			data = (article.title, article.article_body, article.announcement, article.id)
			cur.execute(query, data)
			conn.commit()
			logger.info("Обновлена статья, с id %s", article.id)
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def delete_article(article_id: int) -> None:
	logger.info("Начало удаления статьи %s", article_id)
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor() as cur:
			query = """
                    DELETE
                    FROM articles.articles
                    WHERE article_id = %s;
					"""
			cur.execute(query, (article_id,))
			conn.commit()
			logger.info("Удалена статья %s", article_id)
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении запроса: %s", e)
		raise
	finally:
		if conn:
			conn.close()


def select_articles_by_search(
		query_str: str,
		amount: Optional[int] = None,
		chunk: Optional[int] = None,
		login: Optional[str] = None
) -> list[dict]:
	"""
	Выполняет «умный» поиск по title, announcement и article_body,
	комбинируя полнотекстовый поиск и fuzzy‑поиск на pg_trgm.
	"""
	conn = None
	try:
		conn = connect_pg()
		with conn.cursor(cursor_factory=RealDictCursor) as cur:
			sql = """ 
                  WITH q AS (SELECT plainto_tsquery('russian', %s) AS tsq,
                                    %s::text                       AS rawq),
                       fts AS (SELECT article_id,
                                      ts_rank_cd(search_vector, q.tsq) AS rank_fts
                               FROM articles.articles,
                                    q
                               WHERE search_vector @@ q.tsq),
                       trgm AS (SELECT article_id,
                                       greatest(
                                               similarity(title, q.rawq),
                                               similarity(announcement, q.rawq),
                                               similarity(article_body, q.rawq)
                                       ) AS rank_trgm
                                FROM articles.articles,
                                     q
                                WHERE (coalesce(title, '') || ' ' ||
                                       coalesce(announcement, '') || ' ' ||
                                       coalesce(article_body, ''))
                                          %% q.rawq)
                  SELECT a.article_id,
                         a.title                                 AS title,
                         us.login                                AS login,
                         coalesce(fts.rank_fts, 0) * 1.0
                             + coalesce(trgm.rank_trgm, 0) * 0.5 AS score
                  FROM articles.articles a
                           JOIN users.users us
                                ON a.user_id = us.id
                           LEFT JOIN fts ON fts.article_id = a.article_id
                           LEFT JOIN trgm ON trgm.article_id = a.article_id
				  """
			params: list = [query_str, query_str]

			if login:
				sql += "\nWHERE us.login = %s AND "
				params.append(login)
			else:
				sql += "\nWHERE "
			sql += "(coalesce(fts.rank_fts, 0) * 1.0 + coalesce(trgm.rank_trgm, 0) * 0.5) > 0"

			sql += "\nORDER BY score DESC"

			if amount is not None and chunk is not None:
				sql += "\nOFFSET %s LIMIT %s"
				params.extend([(chunk - 1) * amount, amount])

			cur.execute(sql, params)
			rows = cur.fetchall()
			logger.info("Найдено %d статей по запросу %r", len(rows), query_str)

			return rows
	except (OperationalError, InterfaceError) as e:
		logger.error("Ошибка соединения: %s", e)
		raise
	except Exception as e:
		logger.error("Ошибка при выполнении поиска: %s", e)
		raise
	finally:
		if conn:
			conn.close()
