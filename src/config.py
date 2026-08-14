import os
import sys
import logging

# ============================================================================
# 1. ЗАЩИТА ТЕРМИНАЛА WINDOWS (ФИЛЬТРАЦИЯ МУСОРА ASYNCIO)
# ============================================================================
if sys.platform == "win32":
    asyncio_logger = logging.getLogger("asyncio")
    
    class WindowsSocketNoiseFilter(logging.Filter):
        def filter(self, record):
            return "_call_connection_lost" not in record.getMessage()
            
    asyncio_logger.addFilter(WindowsSocketNoiseFilter())

# ============================================================================
# 2. СКВОЗНАЯ SSO АВТОРИЗАЦИЯ И РЕЕСТР СОТРУДНИКОВ КБ (ИСПРАВЛЕНО ИМЯ)
# ============================================================================
# Автоматически извлекаем логин из сессии ОС Windows по умолчанию
DEFAULT_WINDOWS_USER = os.environ.get("USERNAME", "Радченко П.В.")

# Системный список всех ведущих инженеров КБ для селектора подмены роли
KB_EMPLOYEES = [
    "Радченко П.В.", "Козлов С.С.", "Васильев Н.Н.",
    "Сидоров К.А.", "Алексеев Д.В.", "Кузнецов И.А.",
    "Иванов М.Ю.", "Федоров И.И.", "Смирнов А.А.",
    "Петров А.Н.", "Павлов Р.Д.", "Николаев К.В."
]

# Список системных логинов руководства КБ (Дирекция КБ, Экономисты, Администраторы)
ADMIN_USERS = ["ivanov_av", "petrov_pk", "pavrad", "chief_designer", "pavlov р.д."] 

def check_admin_role(username) -> bool:
    """Проверяет, обладает ли выбранный пользователь правами Управления КБ."""
    return str(username).lower() in ADMIN_USERS

# ============================================================================
# 3. ПОДКЛЮЧЕНИЕ К СУБД POSTGRESQL (ДРАЙВЕР PSYCOPG2)
# ============================================================================
DATABASE_URL = "postgresql+psycopg2://postgres:Avdnm415@localhost:5432/postgres"
