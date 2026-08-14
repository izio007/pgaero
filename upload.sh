#!/bin/bash

# 1. Проверяем или запрашиваем текст коммита
COMMIT_MSG=$1
if [ -z "$COMMIT_MSG" ]; then
    read -r -p "Введите текст коммита: " COMMIT_MSG
fi

# Если пользователь так ничего и не ввел, задаем стандартное сообщение
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Очередное обновление проекта"
fi

# 2. Инициализируем Git, если нужно
if [ ! -d ".git" ]; then
    echo "Инициализация локального Git репозитория..."
    git init
    git config --global init.defaultBranch main
    git branch -M main
fi

# 3. Проверяем, настроен ли удаленный репозиторий
if ! git remote | grep -q "origin"; then
    echo "Удаленный репозиторий (origin) не настроен."
    read -r -p "Укажите ссылку на ваш репозиторий GitHub: " REPO_URL
    
    # Очищаем введенный URL от пробелов и Windows-символов \r (критично для Cygwin)
    REPO_URL=$(echo "$REPO_URL" | tr -d '\r' | xargs)
    
    if [ -z "$REPO_URL" ]; then
        echo "Ошибка: Ссылка на репозиторий обязательна при первой настройке."
        exit 1
    fi
    git remote add origin "$REPO_URL"
fi

# 4. Добавляем файлы, коммитим и отправляем
echo "Добавление изменений..."
git add .

echo "Создание коммита: \"$COMMIT_MSG\"..."
# Проверяем, есть ли вообще что коммитить, чтобы скрипт не падал на пустых изменениях
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "Нет изменений для нового коммита."
else
    git commit -m "$COMMIT_MSG"
fi

echo "Загрузка проекта на GitHub..."
# Используем принудительную отправку --force, так как вы переписывали историю
git push -u origin main --force

echo "Готово! Все изменения успешно загружены."
