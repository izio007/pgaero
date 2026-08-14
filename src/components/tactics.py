import streamlit as st
import pandas as pd
from database import load_level2_tactics

def render_tactics_level(selected_product_id, selected_product_label):
    """
    Рендерит тактическую Pivot-таблицу распределения лимитов времени.
    Выделяет подразделения на 'Критическом пути'.
    ИСПРАВЛЕНО: Старый метод applymap() заменен на современный map().
    """
    st.subheader("🎯 Уровень 2: Тактическое распределение лимитов по подразделениям")
    st.caption(f"Проект воздушного судна: **{selected_product_label}**")
    
    # 1. Загрузка тактических данных из бэкенда КБ
    df = load_level2_tactics(selected_product_id)
    if df.empty:
        st.info("Тактические планы распределения бюджетов часов по отделам для данного изделия отсутствуют.")
        return

    # 2. Вывод предупреждений КБ по критическому пути (Риск сдвига сроков всего самолета вперед)
    st.markdown("##### ⚠️ Распоряжения по критическому пути выполнения:")
    cp_df = df[df["tactical_priority"] == "Критический путь"].drop_duplicates(subset=["department"])
    if not cp_df.empty:
        depts_str = ", ".join([f"**{row['department']}**" for _, row in cp_df.iterrows()])
        st.error(
            f"Внимание! Службы {depts_str} находятся на **Критическом пути**. "
            f"Задержка выпуска КД или проведения расчетов данными отделами автоматически сдвигает сроки сдачи всего самолета!"
        )
    else:
        st.success("Все службы КБ находятся в буферных или магистральных зонах. Прямых рисков сдвига дедлайна изделия нет.")

    st.markdown("---")
    st.markdown("##### 📊 Кросс-матрица распределения заложенных человеко-часов КБ")

    # 3. Разворачиваем плоские строки из базы в кросс-таблицу (Вехи × Отделы) на стороне Python
    pivot_df = df.pivot(index="milestone_name", columns="department", values="allocated_hours").fillna(0)
    
    # Приведение типов к int для красивого отображения в сетке
    pivot_df = pivot_df.astype(int)

    # Цветовая индикация плотности плановой нагрузки на подразделения КБ
    def style_tactical_matrix(val):
        if val == 0: 
            return 'background-color: rgba(0,0,0,0.02); color: #888888; font-style: italic;'
        elif val <= 300: 
            return 'background-color: rgba(232, 245, 233, 0.6); color: #1b5e20; font-weight: bold;' # Комфортный лимит (Зеленый)
        return 'background-color: rgba(255, 224, 178, 0.6); color: #e65100; font-weight: bold;' # Высокая плотность (Оранжевый)

    # Динамическая конфигурация отображения колонок под найденные в базе отделы КБ
    col_config = {col: st.column_config.NumberColumn(col, format="%d ч.") for col in pivot_df.columns}
    col_config["milestone_name"] = st.column_config.TextColumn("Стратегическая веха по Госконтракту", width="large")

    # Сбрасываем индекс, чтобы веха стала обычной колонкой для Streamlit конфигуратора таблицы
    display_df = pivot_df.reset_index()

    # ИСПРАВЛЕНО: Отрисовка тактической матрицы КБ с использованием .style.map() вместо .style.applymap()
    st.dataframe(
        display_df.style.map(style_tactical_matrix, subset=pivot_df.columns),
        column_config=col_config,
        width="stretch",
        hide_index=True
    )
    
    # Сопроводительная легенда матрицы для руководства
    st.markdown(
        "<small>💡 **Как читать тактическую матрицу:** "
        "<span style='background-color: rgba(0,0,0,0.02); padding: 2px 6px;'>0 ч.</span> — отдел не задействован в вехе | "
        "<span style='background-color: #e8f5e9; color: #1b5e20; padding: 2px 6px;'>до 300 ч.</span> — локальные работы | "
        "<span style='background-color: #ffe0b2; color: #e65100; padding: 2px 6px;'>более 300 ч.</span> — пиковая плановая загрузка подразделения.</small>", 
        unsafe_allow_html=True
    )
