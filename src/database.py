import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

@st.cache_resource
def get_db_engine():
    """Создает высокопроизводительный пул соединений SQLAlchemy для Windows-сервера."""
    return create_engine(
        DATABASE_URL,
        pool_size=20,         
        max_overflow=30,      
        pool_timeout=15,
        pool_recycle=1800
    )

engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@st.cache_data(ttl=3600)
def load_products_cached():
    """Загружает список проектов КБ (Синхронизировано со структурой dbinit.sql)."""
    with engine.connect() as conn:
        return pd.read_sql_query(
            text("SELECT product_id, name, type FROM products ORDER BY name;"), 
            conn
        )

# ============================================================================
# АВТООПРЕДЕЛЕНИЕ СЛУЖБЫ/ОТДЕЛА СОТРУДНИКА ПО ЛОГИНУ WINDOWS
# ============================================================================
def get_engineer_department(current_user):
    """
    Сканирует базу данных и определяет, к какому конкретно отделу 
    привязан зашедший в Windows инженер (на основе таблицы задач).
    """
    sql = "SELECT tp.department FROM tasks_micro t JOIN tactical_plans tp ON t.tactical_plan_id = tp.tactical_plan_id WHERE t.assigned_engineer = :eng LIMIT 1;"
    with engine.connect() as conn:
        dept = conn.execute(text(sql), {"eng": current_user}).scalar()
        # Если это новый сотрудник или админ, по умолчанию даем КО-1
        return dept if dept else "КО-1 (Фюзеляж)"

# ============================================================================
# УРОВЕНЬ 1: СТРАТЕГИЯ (ВЫБОРКА КОНТРОЛЬНЫХ ВЕХ)
# ============================================================================
@st.cache_data(ttl=2)
def load_level1_strategy(product_id=None):
    """Выгружает стратегические вехи. Если product_id=0 — выгружает ВСЕ вехи завода."""
    sql = """
        SELECT 
            m.milestone_id, 
            m.name, 
            m.baseline_date AS start_date,     
            m.current_deadline AS deadline_date,  
            m.strategic_priority, 
            m.approval_status AS status,
            p.name AS product_name
        FROM milestones_strategy m
        JOIN products p ON m.product_id = p.product_id
        WHERE 1=1
    """
    params = {}
    if product_id and int(product_id) != 0:
        sql += " AND m.product_id = :product_id"
        params["product_id"] = product_id
    sql += " ORDER BY m.baseline_date ASC;"
    
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# ============================================================================
# УРОВЕНЬ 2: ТАКТИКА (ВЫБОРКА СВОДНЫХ ЛИМИТОВ ОТДЕЛОВ)
# ============================================================================
@st.cache_data(ttl=2)
def load_level2_tactics(product_id=None):
    """Собирает тактические планы отделов. Если product_id=0 — собирает по всему КБ."""
    sql = """
        SELECT m.name as milestone_name, tp.department, tp.allocated_hours, tp.tactical_priority
        FROM tactical_plans tp
        JOIN milestones_strategy m ON tp.milestone_id = m.milestone_id
        WHERE 1=1
    """
    params = {}
    if product_id and int(product_id) != 0:
        sql += " AND m.product_id = :product_id"
        params["product_id"] = product_id
    sql += " ORDER BY m.baseline_date ASC, tp.sort_order;"
    
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# ============================================================================
# УРОВЕНЬ 3: МИКРОМЕНЕДЖМЕНТ (ЖЕСТКАЯ СУБД-ИЗОЛЯЦИЯ ПОД ОТДЕЛ И ТЕКУЩИЙ МЕСЯЦ)
# ============================================================================
@st.cache_data(ttl=2)
def load_hot_active_tasks_isolated(product_id, target_department, search_query=None):
    """
    Извлекает оперативные задачи инженеров, СТРОГО ОГРАНИЧИВАЯСЬ рамками 
    целевого отдела (target_department) и рамками текущего месяца (Август 2026).
    """
    sql = """
        SELECT 
            t.task_id, 
            t.title, 
            t.assigned_engineer, 
            t.task_priority, 
            t.is_completed,
            t.display_weight,
            t.specialization,
            tp.department, 
            m.name as milestone_name, 
            p.name as product_name,
            tp.allocated_hours as plan_hours
        FROM tasks_micro t
        JOIN tactical_plans tp ON t.tactical_plan_id = tp.tactical_plan_id
        JOIN milestones_strategy m ON tp.milestone_id = m.milestone_id
        JOIN products p ON m.product_id = p.product_id
        WHERE t.is_completed = FALSE                          -- Только активные
          AND tp.department = :dept                            -- ЖЕСТКИЙ СЛУЖЕБНЫЙ ФИЛЬТР
          AND tp.deadline_week >= '2026-08-01'                 -- Текущий месяц
          AND tp.start_week <= '2026-08-31'
    """
    params = {"dept": target_department}
    
    # Если в шапке выбран конкретный проект, фильтруем по нему, иначе (Все проекты) — смотрим весь завод по своему отделу
    if product_id and int(product_id) != 0:
        sql += " AND m.product_id = :product_id"
        params["product_id"] = product_id
        
    if search_query:
        sql += " AND (t.title ILIKE :q OR t.assigned_engineer ILIKE :q OR m.name ILIKE :q)"
        params["q"] = f"%{search_query}%"
        
    sql += """ 
        ORDER BY t.display_weight DESC, 
                 CASE t.task_priority WHEN 'Блокирующая' THEN 1 WHEN 'Высокая' THEN 2 ELSE 3 END, 
                 t.task_id DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# ============================================================================
# АНАЛИТИКА: СКВОЗНОЙ ПОИСК БУТЫЛОЧНЫХ ГОРЛЫШЕК ФИНАНСИРОВАНИЯ ГОЗ
# ============================================================================
@st.cache_data(ttl=2)
def check_goz_bottlenecks(product_id):
    """Ищет блокирующие задачи. Если product_id=0 — сканирует все заводы разом."""
    sql = """
        SELECT 
            m.name as milestone_name,
            tp.department,
            t.title as task_title,
            t.assigned_engineer
        FROM tasks_micro t
        JOIN tactical_plans tp ON t.tactical_plan_id = tp.tactical_plan_id
        JOIN milestones_strategy m ON tp.milestone_id = m.milestone_id
        WHERE m.strategic_priority = 'Критический (ГОЗ)'
          AND tp.tactical_priority = 'Критический путь'
          AND t.task_priority = 'Блокирующая'
          AND t.is_completed = FALSE
    """
    params = {}
    if product_id and int(product_id) != 0:
        sql += " AND m.product_id = :product_id"
        params["product_id"] = product_id
        
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)
