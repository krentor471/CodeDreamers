# CodeDreamers — Документация паттернов и реализаций

## Соответствие требованиям

---

## Этап 1

| Требование | Реализация |
|------------|-----------|
| Создание приложения | Flask-приложение (`app.py`), запуск через `python app.py` |
| Создание БД | SQLite, инициализация в `database.py` → `_init_tables()` |
| Запуск базового приложения | `app.run(debug=True, port=5000)` |
| Схема BPMN | 2 основных БП: запись студента на курс + учебный процесс (Template Method в `lesson_process.py`) |
| Сущности и атрибуты | `users`, `courses`, `lessons`, `enrollments`, `course_tags`, `notifications`, `course_packages` |
| Математическая модель | Косинусное сходство векторов тегов (`recommendation_service.py`) — `similarity(A,B) = (A·B)/(|A|·|B|)` |
| Стратегии, состояния, синглтоны | `NotificationStrategy`, `CourseState` / `EnrollmentState`, `ConfigManager` / `DatabaseManager` / `EventBus` |

---

## Этап 2

| Требование | Реализация |
|------------|-----------|
| Схема ERD | Таблицы: `users`, `courses`, `lessons`, `enrollments`, `course_tags`, `notifications`, `course_packages`, `audit_log` |
| Заполнение БД | `seed.py` — 20+ записей: пользователи, курсы, уроки, теги, записи |
| Шаблонный метод| `BaseLessonProcess.execute()` (`lesson_process.py`) — фиксированный порядок шагов, делегирование `check_module_by_teacher()` подклассам `PythonLessonProcess`, `MathLessonProcess`, `WebLessonProcess` |
| Стратегии | `EmailNotification`, `SMSNotification`, `TelegramNotification` (`notification_strategy.py`) — сохраняют факт отправки в БД |
| Математическая модель | `recommend_courses()` + `cosine_similarity()` (`recommendation_service.py`) |
| Абстрактная Фабрика + Декоратор | `BasicPackageFactory`, `StandardPackageFactory`, `PremiumPackageFactory` (`abstract_factory.py`) + `CourseBuilder` с декораторами `CertificateDecorator`, `MentorSupportDecorator`, `LifetimeAccessDecorator` (`course_decorator.py`) |

---

## Этап 3

| Требование | Реализация |
|------------|-----------|
| Обновление машины состояний | `CourseContext` (`course_state.py`): `new → assigned_mentor → assigned_user → in_progress → completed`; `EnrollmentContext` (`enrollment_state.py`): `active ↔ completed ↔ cancelled` |
| Адаптер (новый модуль) | `AIAdapter` (`ai_adapter.py`) — адаптирует `ExternalAI` (g4f) к интерфейсу `IAIService`; `AnalyticsAdapter` (`analytics_adapter.py`) — адаптирует внешнюю аналитику |
| Наблюдатель | `EventBus` (`event_bus.py`) — Singleton + Observer; события: `EnrollEvent`, `CompleteEvent`, `UnenrollEvent`, `StateChangedEvent`, `LessonAddedEvent`, `NotificationEvent`; SSE-push в браузер через `/api/events` |
| Команда | `EnrollCommand`, `UnenrollCommand`, `CompleteCourseCommand` (`course_commands.py`); `CreateCourseCommand`, `AddLessonCommand`, `RevenueReportCommand`, `TopStudentsCommand` (`system_commands.py`); `CommandHistory` с поддержкой `undo` |
| Шаблонный метод | `CourseProcessFactory.run()` делегирует выполнение нужному подклассу по `difficulty_level` курса |

---

## Этап 4

| Требование | Реализация |
|------------|-----------|
| Оформление UI | SPA на чистом JS (`static/`): каталог курсов, детали, создание, админ-панель, AI-чат, вектор рекомендаций |
| Заместитель (Proxy) | `CourseServiceProxy` (`course_service_proxy.py`) — контроль доступа по роли (`student/mentor/admin`) + кэширование запросов к БД |
| Компоновщик + Итератор | `LearningProgram → CourseBlock → LessonItem` (`learning_composite.py`); `LearningIterator` — DFS-обход дерева (`learning_iterator.py`) |
| Обновление диаграммы классов | Отражает все паттерны: Singleton, Strategy, State, Command, Observer, Adapter, Proxy, Composite, Iterator, Template Method, Abstract Factory, Decorator, Facade |

---

## Бэкенд — реализованные требования

### Паттерны

| Паттерн | Файл | Описание |
|---------|------|----------|
| **Singleton** | `config.py` | `ConfigManager` — единственный экземпляр конфигурации |
| **Singleton** | `database.py` | `DatabaseManager` — единственное соединение с SQLite |
| **Singleton** | `patterns/observer/event_bus.py` | `EventBus` — единственная шина событий |
| **Strategy** | `patterns/strategy/notification_strategy.py` | `EmailNotification`, `SMSNotification`, `TelegramNotification` — взаимозаменяемые стратегии отправки |
| **State (курс)** | `patterns/state/course_state.py` | `new → assigned_mentor → assigned_user → in_progress → completed` |
| **State (запись)** | `patterns/state/enrollment_state.py` | `active ↔ completed ↔ cancelled` с синхронизацией в БД |
| **Command** | `patterns/command/course_commands.py` | `EnrollCommand`, `UnenrollCommand`, `CompleteCourseCommand`, `DeleteCourseCommand` + `CommandHistory.undo()` |
| **Command** | `patterns/command/system_commands.py` | `CreateCourseCommand`, `AddLessonCommand`, `ChangeStateCommand`, `SendNotificationCommand`, `RevenueReportCommand`, `TopStudentsCommand` |
| **Observer** | `patterns/observer/event_bus.py` | Публикация/подписка на события; SSE-стрим к клиенту |
| **Observer** | `services/system_observers.py` | `AuditObserver`, `AnalyticsObserver` — подписаны на все события |
| **Adapter (AI)** | `patterns/adapter/ai_adapter.py` | `ExternalAI` (g4f) → `AIAdapter` → `IAIService`; методы: `ask()`, `suggest_tags()`, `generate_quiz()` |
| **Adapter (Analytics)** | `patterns/adapter/analytics_adapter.py` | Адаптирует внешнюю аналитику к системному интерфейсу |
| **Proxy** | `patterns/proxy/course_service_proxy.py` | Контроль доступа по роли + кэш в памяти |
| **Composite** | `patterns/composite/learning_composite.py` | `LearningProgram → CourseBlock → LessonItem` |
| **Iterator** | `patterns/iterator/learning_iterator.py` | DFS-обход дерева `LearningComponent` |
| **Template Method** | `patterns/template/lesson_process.py` | `BaseLessonProcess.execute()` — фиксированный BPMN-процесс, `check_module_by_teacher()` — делегируется подклассам |
| **Template Method** | `patterns/template/content_generator.py` | Генерация контента курса |
| **Abstract Factory** | `patterns/factory/abstract_factory.py` | `BasicPackageFactory`, `StandardPackageFactory`, `PremiumPackageFactory` |
| **Decorator** | `patterns/decorator/course_decorator.py` | `CertificateDecorator`, `MentorSupportDecorator`, `LifetimeAccessDecorator` |
| **Facade** | `services/course_facade.py` | `CourseFacade` — единая точка входа для всех операций с курсами |

### AI как Адаптер

```
IAIService (Target)          ← интерфейс системы
    └── AIAdapter (Adapter)  ← адаптирует ExternalAI к IAIService,
                                обогащает запросы контекстом курса из БД
            └── ExternalAI (Adaptee) ← g4f.ChatCompletion.create()
```

Методы `AIAdapter`:
- `ask(course_id, question)` — вопрос о курсе с контекстом из БД
- `suggest_tags(description)` — генерация тегов по описанию
- `generate_quiz(topic, count)` — генерация quiz-вопросов

### Математическая модель

Косинусное сходство (`recommendation_service.py`):
```
similarity(student, course) = (profile · course_vec) / (|profile| × |course_vec|)
```
- Профиль студента = сумма векторов тегов пройденных курсов (завершённые имеют вес ×2)
- Результат отображается на Canvas как полярный график (`/api/users/<id>/vector`)

---

## Фронтенд — реализованные требования

| Требование | Реализация |
|------------|-----------|
| Создание курсов | Страница `+ Курс` (только `admin`/`mentor`) — название, описание, цена, категория; **использует Command API с возможностью отмены** |
| Сборка курса из модулов | Динамический список уроков с полями название/содержание, отправляется через `POST /api/command/execute` |
| Выставление тегов | Ручной ввод + кнопка "✨ AI теги" (`POST /api/tags/suggest` → `AIAdapter.suggest_tags()`) |
| Отрисовка вектора | Canvas (`page-vector`) — полярный график косинусного сходства по всем курсам |
| Вопросы к AI | Floating-виджет `🤖 AI Ассистент` — `POST /api/chat` → `g4f` |
| Push-уведомления (Observer) | SSE `/api/events` → тосты для системных событий; `NotificationEvent` от админа накапливается в дропдауне колокольчика |
| Состояния курса | Чипы состояния (`new`, `assigned_mentor`, `assigned_user`, `in_progress`, `completed`) на карточках и деталях курса; **изменение через Command с undo** |
| Ролевая модель | `student` — только просмотр; `mentor` — + создание курсов; `admin` — + админ-панель (аналитика, состояния, пользователи, рассылка) |
| **Отмена команд** | Кнопка "⤶ Отменить последнюю команду" в админ-панели; кнопки удаления курсов (🗑️) для админов; все действия интерфейса поддерживают undo |

---

## Структура проекта

```
CodeDreamers/
├── app.py                          # Flask API, все роуты
├── database.py                     # Singleton: DatabaseManager
├── config.py                       # Singleton: ConfigManager
├── seed.py                         # Заполнение БД (20+ записей)
├── models/
│   ├── course.py                   # Модель Course
│   ├── lesson.py                   # Модель Lesson
│   └── user.py                     # Модель User
├── patterns/
│   ├── adapter/
│   │   ├── ai_adapter.py           # Adapter: ExternalAI(g4f) → IAIService
│   │   └── analytics_adapter.py    # Adapter: внешняя аналитика
│   ├── command/
│   │   ├── course_commands.py      # Command: Enroll/Unenroll/Complete + History
│   │   └── system_commands.py      # Command: CreateCourse/AddLesson/Reports
│   ├── composite/
│   │   └── learning_composite.py   # Composite: Program → Block → Lesson
│   ├── decorator/
│   │   └── course_decorator.py     # Decorator: Certificate/MentorSupport/Lifetime
│   ├── factory/
│   │   ├── abstract_factory.py     # Abstract Factory: Basic/Standard/Premium
│   │   ├── course_factory.py       # Factory: создание курсов
│   │   └── user_factory.py         # Factory: создание пользователей
│   ├── iterator/
│   │   └── learning_iterator.py    # Iterator: DFS по дереву LearningComponent
│   ├── observer/
│   │   ├── event_bus.py            # Singleton + Observer: EventBus, все события
│   │   └── course_observer.py      # Observer: подписчики на события курса
│   ├── proxy/
│   │   └── course_service_proxy.py # Proxy: контроль доступа + кэш
│   ├── state/
│   │   ├── course_state.py         # State: машина состояний курса (5 состояний)
│   │   └── enrollment_state.py     # State: машина состояний записи (3 состояния)
│   ├── strategy/
│   │   └── notification_strategy.py # Strategy: Email/SMS/Telegram
│   └── template/
│       ├── lesson_process.py       # Template Method: BPMN учебного процесса
│       └── content_generator.py    # Template Method: генерация контента
├── services/
│   ├── course_facade.py            # Facade: единая точка входа для операций
│   ├── recommendation_service.py   # Математическая модель: косинусное сходство
│   ├── analytics_service.py        # Аналитика
│   ├── student_observer.py         # Observer: подписчик для студентов
│   └── system_observers.py         # Observer: Audit + Analytics
└── static/
    ├── index.html                  # SPA: разметка всех страниц
    ├── app.js                      # SPA: логика, SSE, Canvas, AI-чат
    └── style.css                   # Стили (dark theme)
```

---

## Подробное описание паттернов — где и как работает

---

### Математическая модель — Косинусное сходство

**Файл:** `services/recommendation_service.py`

**Суть:** Каждый курс представлен вектором тегов — словарём вида `{"python": 1, "web": 1, "beginner": 1}`. Профиль студента строится как сумма векторов всех курсов, на которые он записан. Завершённые курсы имеют вес ×2, так как они сильнее отражают интересы студента.

**Формула:**
```
similarity(A, B) = (A · B) / (|A| × |B|)
```
где `A · B` — скалярное произведение (сумма произведений общих тегов), `|A|` и `|B|` — длины векторов (корень из суммы квадратов значений).

**Как работает в системе:**
1. При запросе `GET /api/users/<id>/recommendations` вызывается `recommend_courses(user_id)`
2. Строится профиль студента через `_get_student_profile()` — обходит все его записи в `enrollments`, суммирует теги курсов
3. Для каждого курса, на который студент **не** записан, считается `cosine_similarity(profile, course_vec)`
4. Курсы сортируются по убыванию сходства, возвращается топ-N

**Визуализация:** `GET /api/users/<id>/vector` → `CourseFacade.get_recommendation_vector()` → Canvas на странице "Вектор" рисует полярный график, где длина каждого вектора = similarity, цвет = курс, яркость = записан/не записан.

---

### Стратегия (Strategy)

**Файл:** `patterns/strategy/notification_strategy.py`

**Суть:** Определяет семейство алгоритмов отправки уведомлений, инкапсулирует каждый и делает их взаимозаменяемыми. Объект `User` хранит ссылку на стратегию и делегирует ей отправку.

**Реализованные стратегии:**
- `EmailNotification` — читает `email_host` из `ConfigManager`, логирует и сохраняет в таблицу `notifications`
- `SMSNotification` — читает `sms_api_key`, аналогично
- `TelegramNotification` — читает `telegram_bot_token`, аналогично

**Как работает в системе:**
- `UserFactory` при создании пользователя назначает стратегию по умолчанию из `DEFAULT_STRATEGY` (student → Email, mentor → Telegram, admin → SMS)
- `ChangeStrategyCommand.execute()` меняет стратегию у конкретного пользователя с поддержкой `undo`
- Каждый вызов `user.notify(message)` делегируется текущей стратегии, которая сохраняет факт отправки в БД

---

### Состояние (State)

**Файлы:** `patterns/state/course_state.py`, `patterns/state/enrollment_state.py`

#### Машина состояний курса (`CourseContext`)

**5 состояний:**
```
new → assigned_mentor → assigned_user → in_progress → completed
```

Каждое состояние — отдельный класс (`NewCourseState`, `AssignedToMentorState` и т.д.), реализующий методы `assign_mentor()`, `assign_user()`, `start_progress()`, `complete()`. Недопустимые переходы возвращают сообщение об ошибке без исключения.

**Как работает:** `POST /api/courses/<id>/state` с `{"action": "assign_mentor"}` → `CourseFacade.transition_state()` → `CourseContext.load()` загружает текущее состояние из БД → вызывает нужный метод → `_transition()` сохраняет новое состояние в `courses.state` и публикует `StateChangedEvent` в `EventBus`.

#### Машина состояний записи (`EnrollmentContext`)

**3 состояния:**
```
active ↔ completed ↔ cancelled
```

Переходы: `enroll()`, `complete()`, `cancel()`, `reopen()`. Каждый переход синхронизируется с полями `status` и `completed` в таблице `enrollments`.

**Как работает:** `EnrollCommand.execute()` создаёт запись в БД → при повторном вызове загружает `EnrollmentContext` и вызывает `ctx.enroll()` (переход из `cancelled` → `active`). `CompleteCourseCommand` вызывает `ctx.complete()` → `active` → `completed`.

---

### Синглтоны (Singleton)

**Файлы:** `config.py`, `database.py`, `patterns/observer/event_bus.py`

Все три реализованы через `__new__` с проверкой `_instance`:

| Класс | Что хранит | Зачем |
|-------|-----------|-------|
| `ConfigManager` | Словарь настроек (хосты, токены, путь к БД) | Единая точка конфигурации, инициализирует `logging` |
| `DatabaseManager` | Единственное соединение `sqlite3.Connection` | Исключает множественные соединения, инициализирует таблицы |
| `EventBus` | Словарь подписчиков + лог событий | Глобальная шина — любой модуль может публиковать и подписываться |

`DatabaseManager` при первом создании вызывает `_init_tables()` (создаёт все таблицы) и `_migrate()` (добавляет колонку `state` если её нет).

---

### Абстрактная Фабрика (Abstract Factory)

**Файл:** `patterns/factory/abstract_factory.py`

**Суть:** Создаёт семейства связанных объектов — учебных пакетов — без указания конкретных классов. Каждая фабрика знает, какую цепочку декораторов применить к базовому курсу.

**3 фабрики:**
- `BasicPackageFactory` → курс без дополнений
- `StandardPackageFactory` → курс + `WithCertificate` (+$49.99)
- `PremiumPackageFactory` → курс + `WithCertificate` + `WithMentorSupport` + `WithLifetimeAccess` (+$179.97)

**Как работает:** `GET /api/courses/<id>/package?tier=premium` → `CourseFacade.get_package()` → `get_package_factory("premium")` возвращает `PremiumPackageFactory` → `factory.create_package(course)` запускает `CourseBuilder` с тремя декораторами → `build()` сохраняет итоговый пакет в таблицу `course_packages` и возвращает декорированный объект.

---

### Декоратор (Decorator)

**Файл:** `patterns/decorator/course_decorator.py`

**Суть:** Динамически добавляет курсу новые опции, оборачивая его в цепочку декораторов. Каждый декоратор добавляет к цене и описанию свою часть.

**Иерархия:**
```
CourseComponent (ABC)
    ├── Course (реальный объект)
    └── CourseDecorator (базовый декоратор)
            ├── WithCertificate    +$49.99  → "+ [Certificate]"
            ├── WithMentorSupport  +$99.99  → "+ [Mentor Support]"
            └── WithLifetimeAccess +$29.99  → "+ [Lifetime Access]"
```

**`CourseBuilder`** — вспомогательный строитель, позволяет цепочкой вызовов `.add("certificate").add("mentor_support").build()` собрать нужный пакет. При `build()` сохраняет итог в таблицу `course_packages`.

**Как работает:** `ApplyDecoratorCommand.execute()` использует `CourseBuilder` для применения декораторов. Итоговая цена и описание вычисляются рекурсивно — каждый декоратор вызывает `get_price()` / `get_description()` у обёрнутого объекта и добавляет своё.

---

### Адаптер — AI (Adapter)

**Файл:** `patterns/adapter/ai_adapter.py`

**Суть:** Адаптирует несовместимый интерфейс внешней библиотеки `g4f` к интерфейсу `IAIService`, которого ожидает система. Дополнительно обогащает запросы контекстом из БД.

**Структура:**
```
IAIService (Target)           ← интерфейс, который ожидает система
    └── AIAdapter (Adapter)   ← переводит вызовы системы в вызовы ExternalAI,
        │                        загружает контекст курса из БД
        └── ExternalAI (Adaptee) ← g4f.ChatCompletion.create()
                                   принимает только plain-текст prompt
```

**Три метода адаптера:**

1. **`ask(course_id, question)`** — загружает из БД название, описание, теги курса → формирует prompt с контекстом → передаёт в `ExternalAI.query()` → сохраняет диалог в таблицу `notifications` с каналом `ai_chat`

2. **`suggest_tags(description)`** — передаёт описание в `ExternalAI.suggest()` с промптом "suggest 5 lowercase tags" → парсит ответ по запятым → возвращает список тегов

3. **`generate_quiz(topic, count)`** — формирует промпт с требованием формата `Q: ...|A: ...` → парсит каждую строку ответа → возвращает список `[{"question": ..., "answer": ...}]`

**Как работает в системе:**
- `POST /api/chat` → `g4f` напрямую (общий чат без контекста курса)
- `POST /api/courses/<id>/ask` → `CourseFacade.ask_ai()` → `AIAdapter.ask()` (с контекстом курса)
- `POST /api/tags/suggest` → `CourseFacade.suggest_tags()` → `AIAdapter.suggest_tags()`
- `POST /api/quiz` → `CourseFacade.generate_quiz()` → `AIAdapter.generate_quiz()`

---

### Команда (Command)

**Файлы:** `patterns/command/course_commands.py`, `patterns/command/system_commands.py`

**Суть:** Инкапсулирует запрос как объект, позволяя параметризовать клиентов с различными запросами, ставить запросы в очередь и поддерживать отмену операций.

**`CommandHistory`** — хранит историю выполненных команд, реализует `undo_last()`.

**Реализованные команды:**

| Команда | execute() | undo() |
|---------|-----------|--------|
| `EnrollCommand` | Создаёт запись в `enrollments`, публикует `EnrollEvent` | Вызывает `ctx.cancel()` через State Machine |
| `UnenrollCommand` | Вызывает `ctx.cancel()` | Вызывает `ctx.reopen()` |
| `CompleteCourseCommand` | Вызывает `ctx.complete()`, публикует `CompleteEvent` | Вызывает `ctx.reopen()` |
| `CreateCourseCommand` | Создаёт курс через `CourseFactory`, сохраняет в БД | Удаляет курс и теги из БД |
| `AddLessonCommand` | Вставляет урок в `lessons`, публикует `LessonAddedEvent` | Удаляет урок по `lastrowid` |
| `ApplyDecoratorCommand` | Строит пакет через `CourseBuilder`, сохраняет в `course_packages` | Удаляет пакет из БД |
| `RevenueReportCommand` | Запрашивает отчёт через `AnalyticsAdapter` | Очищает результат (read-only) |
| `TopStudentsCommand` | Запрашивает топ через `AnalyticsAdapter` | Очищает результат (read-only) |
| `CreateUserCommand` | Создаёт пользователя через `UserFactory` | Удаляет пользователя из БД |
| `ChangeStrategyCommand` | Меняет стратегию уведомлений у пользователя | Восстанавливает прежнюю стратегию |

**Как работает:** Все операции в `CourseFacade` проходят через `CommandHistory().execute(cmd)`. Это гарантирует единообразие — каждое действие логируется, может быть отменено, и не зависит от того, кто его вызвал (API, тест, скрипт).

---

### Компоновщик (Composite)

**Файл:** `patterns/composite/learning_composite.py`

**Суть:** Компонует объекты в древовидные структуры для представления иерархий "часть-целое". Клиент работает с отдельными объектами и их композициями единообразно.

**Иерархия:**
```
LearningProgram (корень, тип "program")
    └── CourseBlock (составной узел, тип "block")
            └── LessonItem (лист, тип "lesson")
```

Все три класса реализуют интерфейс `LearningComponent` с методами `get_title()`, `get_children()`, `get_type()`, `to_dict()`.

**Как работает:**
- `CourseServiceProxy.get_program(course_id)` загружает уроки из БД и группирует их по блокам (каждые 3 урока = 1 блок)
- Строит дерево: `LearningProgram` → несколько `CourseBlock` → `LessonItem` в каждом
- `to_dict()` рекурсивно сериализует дерево в JSON
- `GET /api/courses/<id>/program` возвращает это дерево фронтенду
- На фронте `renderProgram()` рекурсивно рендерит блоки с раскрывающимися секциями и уроками

**Итератор по дереву:** `LearningIterator` (`patterns/iterator/learning_iterator.py`) обходит дерево в глубину (DFS) через стек, возвращая только листья — `LessonItem`. Используется когда нужно перебрать все уроки программы без знания структуры дерева.
