# Установка и запуск payroll-sender на Windows без консоли

Эта инструкция поможет пользователю Windows настроить локальный запуск приложения без видимого окна терминала.

---

## 1. Установка Python

1. Перейдите на официальный сайт Python: [https://www.python.org/downloads/](https://www.python.org/downloads/)  
2. Скачайте последнюю стабильную версию Python 3.x (рекомендуется 3.11+) для Windows.  
3. При установке обязательно отметьте:
   - **Add Python to PATH**  
   - **Install for all users** (по желанию)  
4. Проверьте установку в PowerShell:
   ```powershell
   python --version
   pip --version
   ```

---

## 2. Скачивание и подготовка проекта

1. Клонируйте репозиторий:
   ```powershell
   git clone https://github.com/cloud65/payroll-sender.git
   cd payroll-sender
   ```
2. Создайте виртуальное окружение:
   ```powershell
   python -m venv venv
   ```
3. Активируйте виртуальное окружение:
   ```powershell
   .\venv\Scripts\Activate.ps1  # PowerShell
   ```
4. Установите зависимости:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта или задайте переменные вручную через PowerShell:

```powershell
$env:RP_CACHE_DIR="C:\Users\<User>\payroll_cache"
$env:RP_LOG_LEVEL="info"
$env:RP_EMAIL_HOST="smtp.example.com"
$env:RP_EMAIL_PORT=587
$env:RP_EMAIL_USERNAME="user@example.com"
$env:RP_EMAIL_PASSWORD="password"
```

> Замените `<User>` и данные SMTP на ваши реальные значения.

---

## 4. Создание скрипта запуска без консоли

1. В корне проекта создайте файл `run.pyw`:

```python
import logging
import uvicorn

# Логирование в файл
logging.basicConfig(filename="payroll.log", level=logging.INFO)
logging.info("Starting payroll-sender")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
```

- Расширение `.pyw` запускает скрипт **без окна консоли**.

---

## 5. Создание ярлыка для запуска

1. Щёлкните правой кнопкой мыши на рабочем столе → **Создать → Ярлык**  
2. В поле расположения введите путь к `pythonw.exe` с вашим скриптом, например:

```text
C:\Users\<User>\payroll-sender\venv\Scripts\pythonw.exe C:\Users\<User>\payroll-sender\run.pyw
```

3. Нажмите **Далее** → дайте имя ярлыку, например `Payroll Sender` → **Готово**  

Теперь двойной клик по ярлыку запустит приложение **без видимого окна терминала**.

---

## 6. Автоматический запуск при входе в Windows (опционально)

1. Нажмите `Win+R` → введите `shell:startup` → Enter  
2. Скопируйте ярлык `Payroll Sender` в открывшуюся папку  
3. При следующем входе в Windows приложение будет запускаться автоматически, скрыто.

---

## 7. Просмотр логов

Все логи работы приложения пишутся в файл `payroll.log` в корне проекта.  
Откройте его любым текстовым редактором для проверки работы сервера или ошибок.

---

## ✅ Готово!

Теперь приложение работает локально на Windows без видимой консоли и с логированием.

