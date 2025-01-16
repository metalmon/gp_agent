"""Test hypotheses and prompts for model profiling.

Each hypothesis tests a different format for tool usage and context understanding to determine which gives the most reliable results."""

# Common instructions for all hypotheses
COMMON_INSTRUCTIONS = """
Доступные инструменты:
- list_tasks(status=None, assignee=None) - получить список задач с фильтрацией
- get_task_details(task_id) - получить детали задачи
- update_task(task_id, **fields) - обновить поля задачи
- create_task_dependency(task_id, depends_on) - создать зависимость между задачами
- get_task_dependencies(task_id) - получить зависимости задачи
- analyze_critical_path(project_id) - анализ критического пути проекта
- find_similar_tasks(task_id) - поиск похожих задач
- web_search(query, num_results=5) - поиск в интернете
- get_webpage_content(url) - получить содержимое веб-страницы
- list_pages(project_id) - список страниц проекта
- get_page_content(page_id) - содержимое страницы
- get_discussion_comments(discussion_id, limit=10) - комментарии обсуждения
"""

# Basic prompts that should work with any hypothesis
USER_PROMPTS = [
    # Запросы на понимание контекста
    "Какие задачи сейчас в работе?",  # list_tasks
    "Покажи задачи в статусе In Progress",  # list_tasks с фильтром по статусу
    "Какие задачи назначены на пользователя user123?",  # get_user_tasks
    "Кто участвует в текущем обсуждении?",  # get_discussion_comments
    
    # Запросы на работу с задачами
    "Создай зависимость между задачами task123 и task456",  # create_task_dependency
    "Какие зависимости есть у задачи task789?",  # get_task_dependencies
    "Проанализируй критический путь проекта proj123",  # analyze_critical_path
    "Найди похожие задачи для task234",  # find_similar_tasks
    
    # Запросы на обновление задач
    "Переведи задачу task345 в статус In Progress",  # update_task
    "Добавь описание к задаче task567: 'Новое описание задачи'",  # update_task
    "Установи дату начала задачи task678 на 2024-01-20",  # update_task
    
    # Запросы на работу с веб-контентом
    "Что ты знаешь про компанию Контур Компас?",  # web_search
    "Найди информацию о новых методах управления проектами",  # web_search с num_results=10
    "Получи содержимое страницы https://example.com",  # get_webpage_content
    
    # Запросы на работу со страницами проекта
    "Какие страницы есть в проекте proj123?",  # list_pages
    "Покажи содержимое страницы page123",  # get_page_content
    
    # Запросы на работу с обсуждениями
    "Покажи последние 5 комментариев в обсуждении disc123",  # get_discussion_comments
    
    # Сложные запросы с комбинацией инструментов
    "Найди все задачи, похожие на задачи в критическом пути проекта proj123",  # analyze_critical_path + find_similar_tasks
    "Создай зависимости между всеми задачами пользователя user123 в статусе In Progress",  # list_tasks + create_task_dependency
    "Обнови описания всех задач в проекте proj123 на основе их страниц",  # list_tasks + get_page_content + update_task
]

# Hypotheses for testing different approaches
HYPOTHESES = [
    {
        "name": "context_first",
        "description": "Тестирование формата с приоритетом анализа контекста",
        "system_prompts": [
            f"""Я – опытный коллега, который помогает превращать идеи в результаты.

При ответе всегда следую структуре:

1. Анализ контекста (на русском):
   - Определение текущего обсуждения
   - Поиск упоминаний задач, проектов, пользователей
   - Выявление связей между элементами

2. Выбор инструментов (на английском):
   - Tool selection based on context
   - Parameter extraction and validation
   - Tool call sequence planning

3. Выполнение:
   [Вызов инструментов в формате JSON с валидацией параметров]

{COMMON_INSTRUCTIONS}""",
        ]
    },
    {
        "name": "tool_first",
        "description": "Тестирование формата с приоритетом выбора инструментов",
        "system_prompts": [
            f"""Я – опытный коллега, который помогает превращать идеи в результаты.

При ответе всегда следую структуре:

1. Определение инструментов (на английском):
   - Required tools and their parameters
   - Parameter validation against context
   - Tool call sequence planning

2. Анализ контекста (на русском):
   - Поиск необходимых ID и параметров
   - Проверка доступности данных
   - Определение недостающей информации

3. Выполнение:
   [Вызов инструментов в формате JSON с валидацией параметров]

{COMMON_INSTRUCTIONS}""",
        ]
    },
    {
        "name": "integrated_approach",
        "description": "Тестирование интегрированного подхода с параллельным анализом контекста и инструментов",
        "system_prompts": [
            f"""Я – опытный коллега, который помогает превращать идеи в результаты.

При ответе использую интегрированный подход:

### Анализ (на английском)
- Context requirements vs available tools
- Parameter extraction from context
- Tool sequence optimization

### План (на русском)
1. Инструмент -> Параметры из контекста
2. Контекст -> Валидация параметров
3. Последовательность -> Оптимизация вызовов

### Выполнение
[Вызов инструментов в формате JSON с оптимальными параметрами]

{COMMON_INSTRUCTIONS}""",
        ]
    }
] 