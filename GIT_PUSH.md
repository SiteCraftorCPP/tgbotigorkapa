# 📤 Инструкция по пушу на GitHub

## Вариант 1: Через веб-интерфейс GitHub

### Шаг 1: Создание репозитория

1. Перейдите на https://github.com/new
2. Название репозитория: `tgbotigorkapa` (или любое другое)
3. Описание: `Автоматизированный крипто-сигнальный бот для фьючерсов с Telegram интеграцией`
4. Выберите **Private** (рекомендуется) или **Public**
5. **НЕ** создавайте README, .gitignore, license (они уже есть)
6. Нажмите **Create repository**

### Шаг 2: Пуш кода

GitHub покажет инструкции. Выполните в PowerShell:

```powershell
cd "C:\Users\MOD PC COMPANY\Desktop\tgbotigorkapa"

git remote add origin https://github.com/ВАШ_USERNAME/tgbotigorkapa.git

git branch -M main

git push -u origin main
```

При запросе логина/пароля:
- **Логин**: ваш GitHub username
- **Пароль**: используйте **Personal Access Token** (не обычный пароль!)

### Как получить Personal Access Token:

1. https://github.com/settings/tokens
2. **Generate new token (classic)**
3. Выберите срок действия
4. Отметьте галочки:
   - ✅ `repo` (полный доступ к репозиториям)
5. Нажмите **Generate token**
6. **СОХРАНИТЕ токен** - он показывается один раз!
7. Используйте токен вместо пароля при пуше

## Вариант 2: Через GitHub CLI

### Установка GitHub CLI:

```powershell
winget install --id GitHub.cli
```

### Авторизация:

```powershell
gh auth login
```

Следуйте инструкциям (выберите HTTPS, авторизация через браузер).

### Создание репозитория и пуш:

```powershell
cd "C:\Users\MOD PC COMPANY\Desktop\tgbotigorkapa"

# Создать приватный репозиторий
gh repo create tgbotigorkapa --private --source=. --remote=origin --push

# Или публичный
gh repo create tgbotigorkapa --public --source=. --remote=origin --push
```

## Вариант 3: SSH ключи (рекомендуется для постоянной работы)

### Генерация SSH ключа:

```powershell
ssh-keygen -t ed25519 -C "ваш_email@example.com"
```

Сохраните в `C:\Users\MOD PC COMPANY\.ssh\id_ed25519`

### Добавление ключа в SSH agent:

```powershell
# Запуск ssh-agent
Start-Service ssh-agent

# Добавление ключа
ssh-add C:\Users\MOD PC COMPANY\.ssh\id_ed25519
```

### Добавление ключа на GitHub:

1. Скопируйте публичный ключ:

```powershell
cat C:\Users\MOD PC COMPANY\.ssh\id_ed25519.pub | clip
```

2. Перейдите на https://github.com/settings/ssh/new
3. Title: `My PC`
4. Key: вставьте из буфера (Ctrl+V)
5. Нажмите **Add SSH key**

### Пуш через SSH:

```powershell
cd "C:\Users\MOD PC COMPANY\Desktop\tgbotigorkapa"

git remote add origin git@github.com:ВАШ_USERNAME/tgbotigorkapa.git

git branch -M main

git push -u origin main
```

## Проверка успешного пуша

После успешного пуша:

```powershell
git remote -v
```

Должен показать:
```
origin  https://github.com/ВАШ_USERNAME/tgbotigorkapa.git (fetch)
origin  https://github.com/ВАШ_USERNAME/tgbotigorkapa.git (push)
```

## Последующие пуши

После первого пуша, для обновления кода:

```powershell
cd "C:\Users\MOD PC COMPANY\Desktop\tgbotigorkapa"

git add .
git commit -m "Описание изменений"
git push
```

## Важно! 🔐

### Перед пушем убедитесь:

- ✅ `.env` добавлен в `.gitignore` (уже добавлен)
- ✅ API ключи не в коде
- ✅ Пароли БД не в коде
- ✅ Все секретные данные в `.env`

### Проверка:

```powershell
git status
```

Не должно быть файла `.env` в списке для коммита!

## Клонирование на другой машине

```powershell
git clone https://github.com/ВАШ_USERNAME/tgbotigorkapa.git
cd tgbotigorkapa
```

Затем создайте `.env` файл согласно `SETUP.md`.

---

Готово! Ваш код теперь на GitHub 🚀

