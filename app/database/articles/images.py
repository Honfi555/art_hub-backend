"""
Модуль для работы с изображениями в Redis.

Содержит функции для вставки, удаления, получения списка изображений и извлечения байтов
изображения по ключу. Используемые ключи формируются согласно шаблонам и хранятся в Redis.
"""

from logging import Logger
import base64
import uuid

from app.database.connect import connect_redis
from app.logger import configure_logs
from app.models.articles import ImagesAdd

__all__ = ["insert_images", "delete_images", "select_article_images", "get_image_bytes"]
logger: Logger = configure_logs(__name__)

# Шаблоны ключей для хранения данных в Redis
ARTICLE_IMAGES_LIST: str = "article:{article_id}:images"
IMAGE_KEY: str = "image:{article_id}:{image_id}"


def insert_images(images_data: ImagesAdd) -> list[str]:
    """
    Вставляет изображения в Redis и сохраняет связь с соответствующей статьей.

    Для каждого изображения:
    - Декодирует base64 строку в байты.
    - Генерирует уникальный image_id.
    - Сохраняет байты изображения по ключу image:{article_id}:{image_id}.
    - Добавляет image_id в список article:{article_id}:images.

    :param images_data: Объект с идентификатором статьи и списком изображений в формате base64.
    :return: Список сгенерированных image_id для дальнейшего формирования URL.
    """
    redis_client = connect_redis()
    article_id = images_data.article_id
    image_ids: list[str] = []
    for b64 in images_data.images:
        # Декодирование изображения из base64
        img_bytes = base64.b64decode(b64)
        # Генерация уникального идентификатора для изображения
        image_id = str(uuid.uuid4())
        key = f"image:{article_id}:{image_id}"
        # Сохранение байтов изображения в Redis
        redis_client.set(key, img_bytes)
        # Добавление идентификатора изображения в список статьи
        list_key = f"article:{article_id}:images"
        redis_client.rpush(list_key, image_id)
        image_ids.append(image_id)
    logger.info("Redis: вставлено %d изображений для статьи %s", len(image_ids), article_id)
    return image_ids


def delete_images(article_id: int, image_ids: list[str]) -> list[str]:
    """
    Удаляет указанные изображения для данной статьи.

    Для каждого image_id:
    - Удаляет ключ image:{article_id}:{image_id} из Redis.
    - Убирает image_id из списка article:{article_id}:images.

    :param article_id: Идентификатор статьи, из которой удаляются изображения.
    :param image_ids: Список идентификаторов изображений для удаления.
    :return: Список удалённых идентификаторов изображений.
    """
    logger.info("Удаление %d изображений для статьи %s", len(image_ids), article_id)
    client = connect_redis()
    list_key = ARTICLE_IMAGES_LIST.format(article_id=article_id)
    deleted: list[str] = []

    for image_id in image_ids:
        key = IMAGE_KEY.format(article_id=article_id, image_id=image_id)
        # Попытка удаления ключа
        if client.delete(key):
            # Если ключ был, то удаляем UID из списка
            client.lrem(list_key, 0, image_id)
            deleted.append(image_id)

    logger.info("Удалено %d изображений для статьи %s", len(deleted), article_id)
    return deleted


def select_article_images(article_id: int, announce: bool = False) -> list[str]:
    """
    Получает список идентификаторов изображений для заданной статьи.

    :param article_id: Идентификатор статьи.
    :param announce: Если True, возвращает только первый идентификатор изображений.
    :return: Список идентификаторов изображений, закодированных в UTF-8.
    """
    redis_client = connect_redis()
    list_key = f"article:{article_id}:images"
    if announce:
        # Получение только первого элемента списка
        raw_ids = redis_client.lrange(list_key, 0, 0)
    else:
        # Получение всех элементов списка
        raw_ids = redis_client.lrange(list_key, 0, -1)
    # Декодирование идентификаторов из байтов в строковый формат
    image_ids = [rid.decode('utf-8') for rid in raw_ids]
    logger.info("Redis: получено %d image_id для статьи %s (announce=%s)", len(image_ids), article_id, announce)
    return image_ids


def get_image_bytes(article_id: int, image_id: str) -> bytes | None:
    """
    Извлекает байты изображения по-заданному article_id и image_id.

    :param article_id: Идентификатор статьи.
    :param image_id: Идентификатор изображения.
    :return: Байты изображения, либо None если изображение не найдено.
    """
    redis_client = connect_redis()
    key = f"image:{article_id}:{image_id}"
    data = redis_client.get(key)
    if data is None:
        logger.error("Redis: изображение не найдено: %s", key)
    return data
