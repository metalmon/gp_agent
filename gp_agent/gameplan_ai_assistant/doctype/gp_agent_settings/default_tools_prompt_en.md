# Tool Usage Instructions

## Available Tools:

### Search and Information Retrieval
- web_search: Search for information using Google Custom Search API. Parameters:
  - query: Search query string
  - num_results: Number of results to return (default: 5, max: 10)
- get_webpage_content: Fetch and format webpage content. Parameters:
  - url: URL of the webpage to fetch
  Supports:
  - External webpages
  - Frappe documents
  - HTML to markdown conversion
  - Metadata extraction

### Page Management
- create_page: Create a new project page
- update_page: Update an existing page
- get_page_content: Get page content
- list_pages: List project pages

### Task Management
- update_task: Update a task
- get_task_details: Get task details
- list_tasks: List tasks
- get_user_tasks: Get user tasks
- get_task_dependencies: Get task dependencies
- update_task_estimate: Update task estimate
- get_task_estimate_history: Get task estimate history

### Analysis and Prediction
- analyze_critical_path: Analyze critical path
- predict_completion_dates: Predict completion dates
- analyze_team_workload: Analyze team workload
- analyze_estimate_trends: Analyze estimate trends
- analyze_estimate_quality: Analyze estimate quality
- get_team_estimation_metrics: Get team estimation metrics
- analyze_estimate_changes: Analyze estimate changes
- predict_estimate_changes: Predict estimate changes

## Usage Rules:

1. Before using analysis or prediction tools:
   - Analyze all tasks in context
   - Create necessary dependencies using create_task_dependencies

2. When creating dependencies, use types:
   - "Blocks" - when a task blocks another task
   - "Is Blocked By" - when a task is blocked by another task

3. Use tools for their intended purpose:
   - create_task_dependencies - for creating task dependencies
   - analyze_critical_path - for critical path analysis
   - predict_completion_dates - for date predictions
   - analyze_team_workload - for team workload assessment

4. Effectively combine tools:
   - Use web_search to get current information
   - Combine data from different sources
   - But don't rely solely on tools, use experience and context too 