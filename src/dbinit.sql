-- ============================================================================
-- 1. ПОЛНЫЙ СБРОС СТРУКТУРЫ ПОД НОЛЬ
-- ============================================================================
DROP TABLE IF EXISTS workflow_signatures CASCADE;
DROP TABLE IF EXISTS timesheet_monthly CASCADE;
DROP TABLE IF EXISTS tasks_micro CASCADE;
DROP TABLE IF EXISTS tactical_plans CASCADE;
DROP TABLE IF EXISTS milestones_strategy CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- ============================================================================
-- 2. УРОВЕНЬ 0: СПРАВОЧНИК АВИАЦИОННЫХ ПРОЕКТОВ КБ
-- ============================================================================
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,          -- Пример: 'МС-21-310', 'SSJ-New', 'Су-75'
    type VARCHAR(100) NOT NULL
);

-- ============================================================================
-- 3. УРОВЕНЬ 1 (СТРАТЕГИЯ): ДИРЕКТИВНЫЕ ГРАФИКИ И ВЕХИ ГОСКОНТРАКТА
-- ============================================================================
CREATE TABLE milestones_strategy (
    milestone_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,                 -- Наименование контрольного этапа
    baseline_date DATE NOT NULL,                -- Контрактный срок сдачи
    current_deadline DATE NOT NULL,             -- Срок с учетом переносов
    strategic_priority VARCHAR(30) NOT NULL,   -- 'Критический (ГОЗ)', 'Высокий', 'Стандартный'
    approval_status VARCHAR(50) NOT NULL DEFAULT 'Черновик',
    
    CONSTRAINT chk_strat_priority CHECK (strategic_priority IN ('Критический (ГОЗ)', 'Высокий', 'Стандартный')),
    CONSTRAINT chk_approval_status CHECK (approval_status IN ('Черновик', 'На согласовании', 'Утвержден (В отчетах)', 'Снят с контроля'))
);

-- ============================================================================
-- 4. УРОВЕНЬ 2 (ТАКТИКА): ТАКТИЧЕСКИЕ ПЛАНЫ ПОДРАЗДЕЛЕНИЙ
-- ============================================================================
CREATE TABLE tactical_plans (
    tactical_plan_id SERIAL PRIMARY KEY,
    milestone_id INT NOT NULL REFERENCES milestones_strategy(milestone_id) ON DELETE CASCADE,
    department VARCHAR(100) NOT NULL,           -- КО-1 (Фюзеляж), КО-2 (Прочность), КО-3, ОИТ
    allocated_hours INT NOT NULL,               -- Бюджет времени экономиста
    tactical_priority VARCHAR(30) NOT NULL,    -- 'Критический путь', 'Магистральный', 'Буферный'
    start_week DATE NOT NULL,                   -- Неделя старта
    deadline_week DATE NOT NULL,                -- Неделя сдачи
    sort_order INT NOT NULL DEFAULT 0,          -- Порядок для Drag-and-Drop перетаскивания строк
    
    CONSTRAINT chk_tact_hours CHECK (allocated_hours > 0),
    CONSTRAINT chk_tact_priority CHECK (tactical_priority IN ('Критический путь', 'Магистральный', 'Буферный')),
    CONSTRAINT chk_tact_weeks CHECK (deadline_week >= start_week)
);

-- ============================================================================
-- 5. УРОВЕНЬ 3 (МИКРОМЕНЕДЖМЕНТ): ОПЕРАТИВНЫЕ ЗАДАЧИ ИНЖЕНЕРОВ КБ
-- ============================================================================
CREATE TABLE tasks_micro (
    task_id SERIAL PRIMARY KEY,
    tactical_plan_id INT NOT NULL REFERENCES tactical_plans(tactical_plan_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,                -- Текстовка (Редактируется по F2)
    specialization VARCHAR(255) NOT NULL,       -- Специализация работы (Чертеж, Расчет, Код, Тест)
    assigned_engineer VARCHAR(100) NOT NULL,    -- Строго ОДИН ведущий инженер на задачу
    task_priority VARCHAR(30) NOT NULL,        -- 'Блокирующая', 'Высокая', 'Обычная'
    is_completed BOOLEAN NOT NULL DEFAULT FALSE, -- Вычеркивание строки (Флажок выполнения)
    display_weight INT NOT NULL DEFAULT 0,       -- Вес для перебивания вверх при клике
    
    CONSTRAINT chk_task_priority CHECK (task_priority IN ('Блокирующая', 'Высокая', 'Обычная'))
);

-- ============================================================================
-- 6. ТАБЕЛЬ УЧЕТА ВРЕМЕНИ СО СТАТУСОМ И СЧЕТЧИКАМИ (ПОД МЕСЯЦЫ)
-- ============================================================================
CREATE TABLE timesheet_monthly (
    timesheet_id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks_micro(task_id) ON DELETE CASCADE,
    engineer_name VARCHAR(100) NOT NULL,
    year_month VARCHAR(7) NOT NULL,             -- Примеры: '2026-08', '2026-09'
    day_1 NUMERIC(4,2) DEFAULT 0, day_2 NUMERIC(4,2) DEFAULT 0, day_3 NUMERIC(4,2) DEFAULT 0,
    day_4 NUMERIC(4,2) DEFAULT 0, day_5 NUMERIC(4,2) DEFAULT 0, day_6 NUMERIC(4,2) DEFAULT 0,
    day_7 NUMERIC(4,2) DEFAULT 0, day_8 NUMERIC(4,2) DEFAULT 0, day_9 NUMERIC(4,2) DEFAULT 0,
    day_10 NUMERIC(4,2) DEFAULT 0, day_11 NUMERIC(4,2) DEFAULT 0, day_12 NUMERIC(4,2) DEFAULT 0,
    day_13 NUMERIC(4,2) DEFAULT 0, day_14 NUMERIC(4,2) DEFAULT 0, day_15 NUMERIC(4,2) DEFAULT 0,
    day_16 NUMERIC(4,2) DEFAULT 0, day_17 NUMERIC(4,2) DEFAULT 0, day_18 NUMERIC(4,2) DEFAULT 0,
    day_19 NUMERIC(4,2) DEFAULT 0, day_20 NUMERIC(4,2) DEFAULT 0, day_21 NUMERIC(4,2) DEFAULT 0,
    day_22 NUMERIC(4,2) DEFAULT 0, day_23 NUMERIC(4,2) DEFAULT 0, day_24 NUMERIC(4,2) DEFAULT 0,
    day_25 NUMERIC(4,2) DEFAULT 0, day_26 NUMERIC(4,2) DEFAULT 0, day_27 NUMERIC(4,2) DEFAULT 0,
    day_28 NUMERIC(4,2) DEFAULT 0, day_29 NUMERIC(4,2) DEFAULT 0, day_30 NUMERIC(4,2) DEFAULT 0,
    day_31 NUMERIC(4,2) DEFAULT 0,
    is_closed_by_economist BOOLEAN NOT NULL DEFAULT FALSE -- Флажки зеленеют при закрытии экономистом
);

-- ============================================================================
-- 7. ЛИСТ СОГЛАСОВАНИЯ: ЦЕПОЧКА ПОСЛЕДОВАТЕЛЬНЫХ ФЛАЖКОВ С ЗАМЕЧАНИЯМИ
-- ============================================================================
CREATE TABLE workflow_signatures (
    signature_id SERIAL PRIMARY KEY,
    milestone_id INT NOT NULL REFERENCES milestones_strategy(milestone_id) ON DELETE CASCADE,
    approver_name VARCHAR(100) NOT NULL,        -- ФИО согласующего
    step_order INT NOT NULL,                    -- Порядковый номер шага в цепочке
    is_signed BOOLEAN NOT NULL DEFAULT FALSE,    -- Флажок подписи
    remarks TEXT,                               -- Замечания (Видят все)
    signed_at TIMESTAMP
);

-- Высокопроизводительные индексы
CREATE INDEX idx_ms_prod ON milestones_strategy(product_id, approval_status);
CREATE INDEX idx_tp_flow ON tactical_plans(milestone_id, sort_order);
CREATE INDEX idx_tm_prio ON tasks_micro(tactical_plan_id, display_weight DESC, task_priority);
CREATE INDEX idx_ts_monthly_task ON timesheet_monthly(task_id, year_month);
