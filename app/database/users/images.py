from logging import Logger
import base64
import uuid

from ..connect import connect_redis
from ...logger import configure_logs
from ...models.users import UserImagesAdd

__all__ = [
    "insert_user_images",
    "select_user_images",
    "get_user_image_bytes",
    "update_user_image",
]

logger: Logger = configure_logs(__name__)

# Шаблоны ключей для хранения данных в Redis
USER_IMAGES_LIST: str = "user:{user_id}:images"
USER_IMAGE_KEY: str = "user:{user_id}:image:{image_id}"


def insert_user_images(images_data: UserImagesAdd) -> list[str]:
    """
    Вставляет изображения в Redis и сохраняет связь с пользователем.

    Для каждого изображения:
    - Декодирует base64 строку в байты.
    - Генерирует уникальный image_id.
    - Сохраняет байты изображения по ключу user:{user_id}:image:{image_id}.
    - Добавляет image_id в список user:{user_id}:images.

    :param images_data: Объект с идентификатором пользователя и списком изображений (base64).
    :return: Список сгенерированных image_id.
    """
    client = connect_redis()
    user_id = images_data.user_id
    image_ids: list[str] = []

    for b64 in images_data.images:
        img_bytes = base64.b64decode(b64)
        image_id = str(uuid.uuid4())
        key = USER_IMAGE_KEY.format(user_id=user_id, image_id=image_id)
        list_key = USER_IMAGES_LIST.format(user_id=user_id)

        client.set(key, img_bytes)
        client.rpush(list_key, image_id)
        image_ids.append(image_id)

    logger.info(
        "Redis: вставлено %d изображений для пользователя %s",
        len(image_ids),
        user_id,
    )
    return image_ids


def select_user_images(user_id: int, first_only: bool = False) -> list[str]:
    """
    Получает список идентификаторов изображений пользователя.

    :param user_id: Идентификатор пользователя.
    :param first_only: Если True — только первый image_id.
    :return: Список image_id.
    """
    client = connect_redis()
    list_key = USER_IMAGES_LIST.format(user_id=user_id)

    if first_only:
        raw = client.lrange(list_key, 0, 0)
    else:
        raw = client.lrange(list_key, 0, -1)

    ids = [item.decode("utf-8") for item in raw]
    logger.info(
        "Redis: получено %d image_id для пользователя %s (first_only=%s)",
        len(ids),
        user_id,
        first_only,
    )
    return ids


def get_user_image_bytes(user_id: int, image_id: str) -> bytes | None:
    """
    Извлекает байты конкретного изображения пользователя.

    :param user_id: Идентификатор пользователя.
    :param image_id: Идентификатор изображения.
    :return: Байты изображения или None, если не найдено.
    """
    client = connect_redis()
    key = USER_IMAGE_KEY.format(user_id=user_id, image_id=image_id)
    data = client.get(key)
    if data is None:
        logger.error("Redis: изображение не найдено: %s", key)
    else:
        logger.info(
            "Redis: получено изображение %s для пользователя %s", image_id, user_id
        )
    return data


def update_user_image(user_id: int, image_id: str, b64_image: str) -> bool:
    """
    Обновляет (перезаписывает) существующее изображение пользователя.

    :param user_id: Идентификатор пользователя.
    :param image_id: Идентификатор изображения.
    :param b64_image: Новые данные изображения в base64.
    :return: True, если перезапись прошла успешно, False иначе.
    """
    client = connect_redis()
    key = USER_IMAGE_KEY.format(user_id=user_id, image_id=image_id)

    if not client.exists(key):
        logger.error("Redis: не удалось обновить — изображение не найдено: %s", key)
        return False

    img_bytes = base64.b64decode(b64_image)
    client.set(key, img_bytes)
    logger.info("Redis: обновлено изображение %s для пользователя %s", image_id, user_id)
    return True
