import streamlit as st
import pandas as pd
from database import load_level1_strategy, check_goz_bottlenecks

def render_strategy_level(selected_product_id, selected_product_label):
    """
    Рендерит Уровень 1 (Стратегия) под реальный регламент КБ:
    Отображает длинные многонедельные коридоры этапов работ и точечные дедлайны вех.
    """
    st.subheader("🏆 Уровень 1: Стратегический план-график результатов")
    st.caption(f"Проект воздушного судна: **{selected_product_label}**")
    
    # 1. Сквозной риск-мониторинг бутылочных горлышек ГОЗ
    bottlenecks_df = check_goz_bottlenecks(selected_product_id)
    if not bottlenecks_df.empty:
        st.error("🚨 КРИТИЧЕСКИЙ РИСК ОСТАНОВКИ ФИНАНСИРОВАНИЯ ПРОЕКТА (Срыв вехи ГОЗ):")
        for _, row in bottlenecks_df.iterrows():
            st.markdown(
                f"• В рамках вехи **«{row['milestone_name']}»** отдел **{row['department']}** задерживает работы на Критическом пути! "
                f"Причина: блокирующая микрозадача *«{row['task_title']}»* (Ответственный инженер: **{row['assigned_engineer']}**)."
            )
        st.markdown("---")
    else:
        st.success("🛡️ Угрозы срыва финансирования ГОЗ не обнаружено. Все блокирующие задачи КБ закрыты или выполняются в срок.")

    # 2. Загрузка данных вех из бэкенда
    df = load_level1_strategy(selected_product_id)
    if df.empty:
        st.info("Стратегические вехи Госконтракта для данного изделия еще не внесены в базу данных.")
        return

    # Преобразуем даты в формат datetime
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["deadline_date"] = pd.to_datetime(df["deadline_date"])

    # Вычисляем глобальные границы для построения сетки (берем с запасом на весь период)
    global_min = df["start_date"].min()
    global_max = df["deadline_date"].max()
    
    if pd.isna(global_min) or pd.isna(global_max):
        st.warning("Внимание: в базе данных КБ отсутствуют директивные даты вех.")
        return

    # Формируем полный массив недель для колонок таблицы
    all_weeks = pd.date_range(start=global_min, end=global_max, freq='W-MON')
    
    if not all_weeks.empty:
        week_cols = [w.strftime('%Y-W%V') for w in all_weeks]
    else:
        week_cols = [global_min.strftime('%Y-W%V')]
    
    current_week_str = pd.Timestamp.now().strftime('%Y-W%V')

    # СБОРКА ДЛИННЫХ СТРОК ЭТАПОВ
    gantt_rows = []
    for idx, row in df.iterrows():
        # Считаем, что этап начинается с самого начала проекта (или от предыдущей вехи)
        # и длится как длинный коридор вплоть до недели дедлайна сдачи
        corridor_weeks = [w.strftime('%Y-W%V') for w in pd.date_range(start=global_min, end=row["deadline_date"], freq='W-MON')]
        deadline_week_str = row["deadline_date"].strftime('%Y-W%V')

        m_row = {
            "Контрольный результат (Веха)": row["name"],
            "Важность": row["strategic_priority"],
            "🚨 Срок сдачи": row["deadline_date"].strftime("%d.%m.%Y"),
            "Статус": row["status"]
        }
        
        # Заполняем клетки длинной строки
        for w in week_cols:
            if w == deadline_week_str:
                m_row[w] = "🏁 СДАЧА" # Точечный финишный маркер дедлайна в конце строки
            elif w in corridor_weeks:
                m_row[w] = "═══" if row["status"] != "Сдано" else "══✓" # Длинная полоса коридора работ
            else:
                m_row[w] = ""
        gantt_rows.append(m_row)

    gantt_df = pd.DataFrame(gantt_rows)

    # Профессиональное построчное CSS-окрашивание длинных коридоров КБ
    def style_gantt_row(row_data):
        styles = []
        for col_name in gantt_df.columns:
            val = row_data[col_name]
            is_current = (col_name == current_week_str)
            border = 'border-left: 2px solid #ff9100; border-right: 2px solid #ff9100;' if is_current else ''
            
            if val == "🏁 СДАЧА":
                # Выделяем финальный дедлайн ярким красным цветом (или зеленым, если сдано)
                bg = "#2e7d32" if row_data["Статус"] == "Сдано" else "#cc0000"
                styles.append(f'background-color: {bg}; color: white; text-align: center; font-weight: bold; font-size: 11px; {border}')
            elif val in ["═══", "══✓"]:
                # Окрашиваем длинную полосу этапа в глубокий синий или зеленый цвет
                bg = "rgba(46, 125, 50, 0.2)" if row_data["Статус"] == "Сдано" else "rgba(30, 136, 229, 0.2)"
                color = "#2e7d32" if row_data["Статус"] == "Сдано" else "#1e88e5"
                styles.append(f'background-color: {bg}; color: {color}; text-align: center; font-weight: bold; {border}')
            elif is_current:
                styles.append(f'background-color: rgba(255, 145, 0, 0.08); {border}')
            else:
                styles.append('background-color: rgba(0,0,0,0.01);')
        return styles

    # Конфигурация отображения колонок таблицы Ганта
    col_config = {col: st.column_config.TextColumn(f"Нед {col.split('-W')[-1]}", width="small") for col in week_cols}
    col_config["Контрольный результат (Веха)"] = st.column_config.TextColumn("Длинный плановый этап Госконтракта", width="large")
    col_config["🚨 Срок сдачи"] = st.column_config.TextColumn("Дедлайн вехи", width="medium")

    st.markdown("##### 🗺️ Линейный таймлайн прохождения и сдачи долгосрочных этапов")
    
    # Отрисовка длинных строк Ганта на весь экран
    st.dataframe(
        gantt_df.style.apply(style_gantt_row, axis=1),
        column_config=col_config,
        width="stretch",
        hide_index=True
    )
    
    st.markdown(
        "<small>💡 **Легенда Ганта:** Коридор <span style='color:#1e88e5; font-weight:bold;'>═══</span> показывает недели "
        "выполнения длинного этапа КБ | Плашка <span style='background-color:#cc0000; color:white; padding:1px 4px; font-weight:bold;'>🏁 СДАЧА</span> "
        "показывает точечную неделю контрактного дедлайна вехи.</small>", 
        unsafe_allow_html=True
    )
