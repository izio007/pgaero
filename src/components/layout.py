import streamlit as st
from .strategy import render_strategy_level
from .tactics import render_tactics_level
from .micro import render_micro_level

def render_mailbird_layout(selected_product_id, selected_product_label, search_input, is_admin, current_user):
    """
    Разворачивает оригинальный двухпанельный дизайн Mailbird:
    Левый ряд иконок управления + Правое широкое табличное пространство КБ.
    ИСПРАВЛЕНО: Жестко передан обязательный массив пропорций.
    """
    # Гарантируем уникальность кэш-ключей навигации для каждого изделия КБ
    tier_key = f"mailbird_active_tier_{selected_product_id}"
    
    if tier_key not in st.session_state:
        st.session_state[tier_key] = "📋 Микроменеджмент"

    current_tier = st.session_state[tier_key]

    # ЖЕСТКОЕ ИСПРАВЛЕНИЕ: Передаем пропорции [1, 22] для разделения панелей
    nav_panel, workspace_panel = st.columns([1, 22])

    # ============================================================================
    # ПАНЕЛЬ 1: СТРОГАЯ ЛЕВАЯ НАВИГАЦИЯ MAILBIRD (ВЕРТИКАЛЬНЫЙ РЯД ИКОНОК)
    # ============================================================================
    with nav_panel:
        st.markdown("<p style='text-align:center; font-size:10px; font-weight:bold; color:gray; margin-bottom:10px;'>УРОВЕНЬ</p>", unsafe_allow_html=True)
        
        # Кнопка Уровня 1 (Стратегия)
        is_strat = current_tier == "🏆 Стратегия"
        if st.button("🏆", help="Стратегия: Вехи по Госконтракту и ГОЗ", type="primary" if is_strat else "secondary", width="stretch"):
            st.session_state[tier_key] = "🏆 Стратегия"
            st.rerun()
            
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
            
        # Кнопка Уровня 2 (Тактика)
        is_tact = current_tier == "🎯 Тактика"
        if st.button("🎯", help="Тактика: Распределение лимитов времени по отделам КБ", type="primary" if is_tact else "secondary", width="stretch"):
            st.session_state[tier_key] = "🎯 Тактика"
            st.rerun()
            
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
            
        # Кнопка Уровня 3 (Микроменеджмент)
        is_micro = current_tier == "📋 Микроменеджмент"
        if st.button("📋", help="Микроменеджмент: Календарная сетка и Табель инженеров", type="primary" if is_micro else "secondary", width="stretch"):
            st.session_state[tier_key] = "📋 Микроменеджмент"
            st.rerun()

    # ============================================================================
    # ПАНЕЛЬ 2: ШИРОКОЕ РАБОЧЕЕ ПРОСТРАНСТВО (ТАБЛИЦЫ И СЕТКИ)
    # ============================================================================
    with workspace_panel:
        if current_tier == "🏆 Стратегия":
            render_strategy_level(selected_product_id, selected_product_label)
            
        elif current_tier == "🎯 Тактика":
            render_tactics_level(selected_product_id, selected_product_label)
            
        elif current_tier == "📋 Микроменеджмент":
            render_micro_level(selected_product_id, selected_product_label, search_input, is_admin, current_user)
