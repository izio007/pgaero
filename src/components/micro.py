import streamlit as st
import pandas as pd
from sqlalchemy import text
from database import engine, SessionLocal, get_engineer_department, load_hot_active_tasks_isolated
from .calendar_grid import render_month_calendar_grid

def render_micro_level(selected_product_id, selected_product_label, search_input, is_admin, current_user):
    """
    Рендерит Уровень 3: Таблица активных задач СТРОГО внутри родного отдела сотрудника,
    нативная Mailbird календарная сетка и изолированный табель выработки.
    ИСПРАВЛЕНО: current_user теперь прокидывается динамически из селектора pgaero.py.
    """
    # 1. Автоматически определяем отдел вошедшего инженера по выбранному профилю КБ
    user_dept = get_engineer_department(current_user)
    
    # Отрисовываем строгую информационную плашку принадлежности к сектору КБ
    st.info(f"🔒 Авторизация: **{current_user}** | Автоматический фильтр службы: **{user_dept}**")

    if int(selected_product_id) == 0:
        st.write(f"📋 **Уровень 3: Сводный микроменеджмент службы {user_dept} по всем проектам КБ**")
    else:
        st.write(f"📋 **Уровень 3: Микроменеджмент службы {user_dept} — Изделие {selected_product_label}**")
    
    # 2. Загрузка реестра активных задач, изолированных СТРОГО под отдел текущего месяца (Август 2026)
    tasks_df = load_hot_active_tasks_isolated(selected_product_id, user_dept, search_input)
    if tasks_df.empty:
        st.success(f"✅ В отделе {user_dept} нет активных или нераспределенных задач на август 2026 года по выбранному фильтру.")
        return

    st.write(f"🔥 **Оперативный реестр активных задач сектора {user_dept} (Август 2026)**")
    
    # Конфигурация колонок (убираем колонку отдела, так как он зафиксирован, выводим проект)
    col_config = {
        "task_id": "ID",
        "product_name": "Авиапроект",
        "milestone_name": "Стратегическая веха КБ",
        "title": "Наименование конструкторской работы (F2 для правок)",
        "specialization": "Специализация работы",
        "assigned_engineer": "Ответственный ведущий инженер",
        "task_priority": "Приоритет",
        "plan_hours": st.column_config.NumberColumn("План (ч)", format="%d")
    }
    
    cols_to_show = ["task_id", "product_name", "milestone_name", "title", "specialization", "assigned_engineer", "task_priority", "plan_hours"]

    # Вывод реестра активных задач отдела в виде плотной Excel-таблицы на весь экран
    st.dataframe(
        tasks_df[cols_to_show],
        width="stretch",
        hide_index=True,
        column_config=col_config
    )

    st.markdown("---")
    st.write("##### ✍️ Личное календарное расписание и списание человеко-часов")
    
    # Сборка словаря доступных активных задач для вывода на календарь
    task_dict = {f"ID {row['task_id']}: {row['title']} [{row['specialization']}]": row['task_id'] for _, row in tasks_df.iterrows()}
    
    active_task_key = f"active_calendar_task_id_clean_{selected_product_id}"
    
    if active_task_key not in st.session_state or st.session_state[active_task_key] not in task_dict.values():
        st.session_state[active_task_key] = list(task_dict.values())

    selected_task_label = st.selectbox(
        "Выберите активную конструкторскую работу сектора для вывода на календарную сетку месяца:", 
        list(task_dict.keys()),
        key=f"selectbox_task_clean_wrapper_{selected_product_id}"
    )
    
    st.session_state[active_task_key] = task_dict[selected_task_label]
    target_task_id = st.session_state[active_task_key]

    # Вызов нативного Month View календаря (current_user прокинут динамически)
    render_month_calendar_grid(target_task_id, is_admin, current_user)
    
    st.markdown("---")
    st.write(f"##### ✍️ Месячный табель учета часов сотрудников службы {user_dept}")

    # 3. ШАХМАТКА ДНЕЙ 1-31 ДЛЯ ПРОВЕРКИ НАЧАЛЬНИКОМ СЕКТОРА И ЭКОНОМИСТОМ
    with engine.connect() as conn:
        ts_sql = "SELECT * FROM timesheet_monthly WHERE task_id = :id ORDER BY timesheet_id DESC;"
        current_ts_df = pd.read_sql_query(text(ts_sql), conn, params={"id": target_task_id})

    if not current_ts_df.empty:
        cols_to_show = ["engineer_name", "year_month"] + [f"day_{i}" for i in range(1, 32)] + ["is_closed_by_economist"]
        
        edited_ts_df = st.data_editor(
            current_ts_df[cols_to_show],
            width="stretch",
            hide_index=True,
            column_config={
                "engineer_name": st.column_config.TextColumn("Ведущий инженер", disabled=True),
                "year_month": st.column_config.TextColumn("Период", disabled=True),
                "is_closed_by_economist": st.column_config.CheckboxColumn("🔒 Утверждено экономистом", disabled=not is_admin)
            },
            key=f"economist_grid_editor_{target_task_id}"
        )

        if is_admin and st.button("🔒 Утвердить объемы выработки и закрыть месяц по задаче", type="primary", key=f"btn_lock_month_{target_task_id}"):
            session = SessionLocal()
            try:
                state = st.session_state[f"economist_grid_editor_{target_task_id}"]
                if state["edited_rows"]:
                    for r, ch in state["edited_rows"].items():
                        tid = int(current_ts_df.iloc[int(r)]["timesheet_id"])
                        if "is_closed_by_economist" in ch:
                            session.execute(
                                text("UPDATE timesheet_monthly SET is_closed_by_economist = :val WHERE timesheet_id = :id"),
                                {"val": ch["is_closed_by_economist"], "id": tid}
                            )
                session.commit()
                st.success("✅ Статус месяца успешно изменен! Выработка по службе зафиксирована.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Ошибка блокировки СУБД: {e}")
            finally:
                session.close()
    else:
        st.caption("По данной работе сотрудники службы еще не заводили выработку человеко-часов в текущем периоде.")
