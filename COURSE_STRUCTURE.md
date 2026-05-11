# Структура курса в CodeDreamers

## Иерархия

```
Курс (Course)
├── Модуль (Module)
│   ├── Предмет (Discipline)
│   │   └── Урок (Lesson)
│   └── Предмет (Discipline)
│       └── Урок (Lesson)
└── Модуль (Module)
    └── Предмет (Discipline)
        └── Урок (Lesson)
```

## Таблицы БД

### courses
- id, title, description, price, difficulty_level, state

### modules
- id, course_id, title, order_num, teacher_id

### disciplines
- id, title, description, content

### module_disciplines
- id, module_id, discipline_id, order_num

### lessons
- id, course_id, module_id, title, content, order_num

## API Endpoints

### Модули
- `POST /api/courses/<id>/modules` - создать модуль
- `GET /api/courses/<id>/modules` - получить модули курса

### Предметы
- `POST /api/disciplines` - создать предмет
- `GET /api/disciplines` - получить все предметы
- `POST /api/modules/<id>/disciplines` - добавить предмет в модуль
- `DELETE /api/modules/<id>/disciplines/<discipline_id>` - удалить предмет из модуля

### Уроки
- `POST /api/courses/<id>/lessons` - добавить урок (можно с module_id)
- `GET /api/courses/<id>/lessons` - получить уроки курса

## Command Pattern

### CreateModuleCommand
- execute: создает модуль
- undo: удаляет модуль и связи

### AddDisciplineToModuleCommand
- execute: добавляет предмет в модуль
- undo: удаляет связь

### CreateDisciplineCommand
- execute: создает предмет
- undo: удаляет предмет и связи

### AddLessonCommand (обновлен)
- execute: добавляет урок в курс/модуль
- undo: удаляет урок

## Пример использования

1. Создать курс
2. Создать модули для курса
3. Создать предметы
4. Добавить предметы в модули
5. Добавить уроки в предметы (через module_id)