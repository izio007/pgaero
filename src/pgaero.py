import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_WINDOWS_USER, KB_EMPLOYEES, check_admin_role
from database import load_products_cached
from components import render_mailbird_layout

# Максимальная ширина экрана КБ
st.set_page_config(
    layout="wide", 
    page_title="pgaero Workspace", 
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ЛЕВАЯ ПАНЕЛЬ СЕЛЕКТОРОВ MAILBIRD + ИНТЕРАКТИВНЫЙ ВЫБОР ПОЛЬЗОВАТЕЛЯ КБ
# ============================================================================
with st.sidebar:
    st.markdown("<h3 style='margin-top:0px;'>🦅 pgaero КБ</h3>", unsafe_allow_html=True)
    
    # Сборка списка для переключения (Текущий Windows-профиль + все инженеры)
    available_users = list(set([DEFAULT_WINDOWS_USER] + KB_EMPLOYEES))
    
    # Селектор подмены пользователя КБ (Всегда доступен сверху)
    current_user = st.selectbox(
        "👤 Текущий профиль сессии КБ:",
        available_users,
        index=available_users.index(DEFAULT_WINDOWS_USER) if DEFAULT_WINDOWS_USER in available_users else 0,
        key="mailbird_user_switcher"
    )
    
    # Проверяем роль для выбранного в данный момент профиля
    is_admin = check_admin_role(current_user)
    
    if is_admin:
        st.sidebar.success("👑 Управление КБ (Полный доступ)")
    else:
        st.sidebar.info("🛠️ Роль: Конструктор сектора")
        
    st.markdown("---")
    st.write("📂 **Глобальный реестр проектов КБ**")
    
    # Формируем список изделий КБ со строкой «Все проекты»
    product_options = {"🌐 Все проекты КБ": 0}
    products_df = load_products_cached()
    for _, row in products_df.iterrows():
        product_options[f"✈️ {row['name']}"] = row['product_id']

    selected_product_label = st.selectbox(
        "Выберите активный авиапроект:", 
        list(product_options.keys()),
        key="mailbird_global_sidebar_selector"
    )
    selected_product_id = product_options[selected_product_label]
    
    st.markdown("---")
    
    # Сквозная шина живого поиска по контексту задач
    search_input = st.text_input(
        "Живой поиск по задачам КБ:", 
        placeholder="🔍 Введите текст для фильтрации..."
    )

# ============================================================================
# ПРАВОЕ РАБОЧЕЕ ПРОСТРАНСТВО КБ
# ============================================================================
st.markdown(f"<h3 style='margin-top:0px; margin-bottom:0px;'>🦅 {selected_product_label}</h3>", unsafe_allow_html=True)
st.markdown("<hr style='margin-top:5px; margin-bottom:15px;' />", unsafe_allow_html=True)

# Передача управления и выбранного кастомного юзера главному диспетчеру интерфейса
render_mailbird_layout(selected_product_id, selected_product_label, search_input, is_admin, current_user)