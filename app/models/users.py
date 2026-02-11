from pydantic import BaseModel, Field

__all__: list[str] = ["AuthorInfo", "DescriptionUpdate"]


class AuthorInfo(BaseModel):
	"""
	Модель с информацией об авторе.

	:param id: Уникальный идентификатор автора.
	:param author_name: Имя автора.
	:param description: Описание/биография автора.
	"""
	id: int = Field(..., description="Уникальный идентификатор автора")
	author_name: str = Field(..., description="Имя автора")
	description: str = Field(..., description="Описание/биография автора")


class DescriptionUpdate(BaseModel):
	"""
	Модель для обновления описания автора.

	:param description: Новое описание/биография автора.
	"""
	description: str = Field(..., description="Новое описание/биография автора")


class UserImagesAdd(BaseModel):
	"""
	Модель для передачи изображений пользователя.

	:param user_id: Идентификатор пользователя.
	:param images: Список строк с изображениями в формате base64.
	"""
	user_id: int = Field(..., description="Идентификатор пользователя")
	images: list[str] = Field(..., description="Список изображений в формате base64")
