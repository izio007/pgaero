import streamlit as st
import pandas as pd
import calendar
import datetime
from database import engine, SessionLocal
from sqlalchemy import text

def render_month_calendar_grid(selected_task_id, is_admin, current_user):
    """
    Рендерит промышленную календарную сетку месяца КБ на базе нативного st.data_editor.
    Синхронизировано с помесячной структурой полей (day_1 ... day_31) в БД.
    Полностью защищено от ошибок React DOM и адаптировано под width='stretch'.
    """
    st.write("🗓️ **Календарная сетка месяца (Август 2026)**")
    year, month = 2026, 8
    year_month_str = f"{year}-{month:02d}"
    
    # 1. ЗАГРУЗКА ТЕКУЩИХ СПИСАНИЙ ИЗ ПОМЕСЯЧНОЙ ТАБЛИЦЫ СУБД
    with engine.connect() as conn:
        sql = """
            SELECT * 
            FROM timesheet_monthly 
            WHERE task_id = :t_id AND year_month = :ym
        """
        if not is_admin:
            sql += " AND engineer_name = :eng"
        df = pd.read_sql_query(text(sql), conn, params={"t_id": selected_task_id, "ym": year_month_str, "eng": current_user})

    # Преобразуем существующие списания в словарь дня: { день_месяца: часы }
    existing_hours = {}
    if not df.empty:
        row = df.iloc[0]  # Берем первую строку выработки инженера
        for d in range(1, 32):
            val = row.get(f"day_{d}")
            if val and float(val) > 0:
                existing_hours[d] = float(val)

    # 2. ГЕНЕРАЦИЯ МАТРИЦЫ КАЛЕНДАРЯ ДЛЯ DATA_EDITOR
    cal = calendar.Calendar(firstweekday=0)
    month_weeks = cal.monthdayscalendar(year, month)
    days_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    calendar_rows = []
    for week in month_weeks:
        row_data = {}
        for day_idx, day in enumerate(week):
            col_name = days_names[day_idx]
            if day == 0:
                row_data[col_name] = ""
            else:
                hours = existing_hours.get(day)
                if hours:
                    row_data[col_name] = f"[{day:02d} числ.] -> {hours} ч."
                else:
                    row_data[col_name] = f"[{day:02d} числ.]"
        calendar_rows.append(row_data)

    calendar_df = pd.DataFrame(calendar_rows)
    col_config = {day_name: st.column_config.TextColumn(day_name, width="medium") for day_name in days_names}

    st.caption("💡 **Инструкция КБ:** Дважды кликните на ячейку дня, впишите или измените часы в формате `[число числ.] -> часы ч.`, затем нажмите кнопку фиксации снизу.")
    
    # Рендерим полностью безопасный нативный табличный компонент (width="stretch")
    edited_cal_df = st.data_editor(
        calendar_df,
        column_config=col_config,
        width="stretch",
        hide_index=True,
        key=f"mailbird_grid_editor_clean_final_{selected_task_id}"
    )

    # 3. ПАКЕТНАЯ СИНХРОНИЗАЦИЯ С СУБД POSTGRESQL (ПРАВИЛЬНЫЕ ПОЛЯ ШАХМАТКИ ЧАСОВ)
    if st.button("💾 Зафиксировать календарную сетку в PostgreSQL", type="primary", key=f"btn_save_cal_final_{selected_task_id}"):
        session = SessionLocal()
        try:
            state = st.session_state[f"mailbird_grid_editor_clean_final_{selected_task_id}"]
            if state["edited_rows"]:
                # Проверяем, существует ли уже базовая строка табеля на этот месяц в БД
                check_sql = "SELECT timesheet_id FROM timesheet_monthly WHERE task_id = :t_id AND year_month = :ym AND engineer_name = :eng;"
                ts_id = session.execute(text(check_sql), {"t_id": selected_task_id, "ym": year_month_str, "eng": current_user}).scalar()
                
                if not ts_id:
                    # Если строки нет — создаем пустой бланк на текущий рабочий месяц
                    insert_blank = "INSERT INTO timesheet_monthly (task_id, engineer_name, year_month) VALUES (:t_id, :eng, :ym) RETURNING timesheet_id;"
                    ts_id = session.execute(text(insert_blank), {"t_id": selected_task_id, "eng": current_user, "ym": year_month_str}).scalar()

                for row_idx, changes in state["edited_rows"].items():
                    for col_name, new_val in changes.items():
                        if not new_val: continue
                        try:
                            # Извлекаем день и введенные часы из строки вида "[14 числ.] -> 8.5 ч."
                            if "->" in new_val:
                                parts = new_val.split("->")
                                day_part = parts[0].replace("[", "").replace(" числ.]", "").strip()
                                hours_part = parts[1].replace(" ч.", "").strip()
                            else:
                                old_val = calendar_df.iloc[int(row_idx)][col_name]
                                day_part = old_val.replace("[", "").replace(" числ.]", "").split("->")[0].strip()
                                hours_part = new_val.strip()

                            target_day = int(day_part)
                            target_hours = float(hours_part)

                            # Динамически обновляем поле конкретного дня (day_1 ... day_31)
                            update_sql = f"UPDATE timesheet_monthly SET day_{target_day} = :h WHERE timesheet_id = :id"
                            session.execute(text(update_sql), {"h": target_hours, "id": ts_id})
                            
                        except Exception as parse_error:
                            st.error(f"Ошибка формата ячейки. Используйте шаблон: `[число числ.] -> часы ч.`")
                            return
                            
                session.commit()
                st.success("🔒 Календарные часы успешно зафиксированы в PostgreSQL!")
                st.cache_data.clear()
                st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"🚨 Сбой транзакции СУБД: {e}")
        finally:
            session.close()
