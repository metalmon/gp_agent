"""Model profiler for analyzing model responses and patterns."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
from tqdm import tqdm
import frappe
import shutil


class ModelProfiler:
    """Profiler for analyzing model responses and patterns."""

    # ANSI color codes
    HEADER = '\033[95m'      # Purple
    BLUE = '\033[94m'        # Blue
    GREEN = '\033[92m'       # Green
    YELLOW = '\033[93m'      # Yellow
    RED = '\033[91m'         # Red
    ENDC = '\033[0m'         # Reset color
    BOLD = '\033[1m'         # Bold
    
    # Class level storage for output lines
    _output_lines = []
    
    @classmethod
    def get_output_lines(cls):
        """Get the current output lines."""
        return cls._output_lines
    
    def __init__(
        self,
        output_dir: str = "profiling_results",
        stats = None,
        settings = None,
    ):
        """Initialize the profiler.

        Args:
            output_dir: Directory to store profile results
            stats: Statistics tracker object
            settings: Model settings object
        """
        self.settings = settings
        self.api_key = self.settings.get_password('api_key')
        self.output_dir = output_dir
        self.max_retries = self.settings.max_retries
        self.retry_delay = self.settings.retry_delay
        self.stats = stats
        self.credits_info = None  # Информация о кредитах
        self.is_openrouter = 'openrouter.ai' in self.settings.base_url
        self.is_free_model = self.settings.model.endswith(':free')
        self.current_hypothesis = None  # Текущая тестируемая гипотеза
        
        # Tracking for free model limits
        self.minute_requests = []  # Timestamps of requests in the last minute
        self.daily_requests = []   # Timestamps of requests in the last day
        
        if self.is_openrouter:
            self._add_output("OpenRouter API detected, enabling credits tracking", self.BLUE)
            if self.is_free_model:
                self._add_output("Free model detected, enabling request limits tracking (20/min, 200/day)", self.YELLOW)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _add_output(self, message: str, color: str = ""):
        """Добавляет сообщение в историю вывода"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if color:
            self.__class__._output_lines.append(f"{color}[{timestamp}] {message}{self.ENDC}")
        else:
            self.__class__._output_lines.append(f"[{timestamp}] {message}")
        # Keep only last 1000 lines
        if len(self.__class__._output_lines) > 1000:
            self.__class__._output_lines = self.__class__._output_lines[-1000:]

    def _clear_and_print_status(self, current_prompt: str, status: str, error: str, progress_bar=None):
        """Update status via stats object or print directly"""
        if self.stats:
            # Status will be shown via TestStats._print_current_stats
            return
            
        # Fallback for when stats object is not available
        if status:
            print(status)
        if error:
            print(f"{self.RED}{error}{self.ENDC}")
        
        # Show last few log lines
        print("\nRecent logs:")
        for line in self.__class__._output_lines[-5:]:
            print(line)

    def _check_credits(self) -> Dict:
        """Checks available credits and rate limits for the API key"""
        if not self.is_openrouter:
            return None
            
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.settings.request_timeout
            )
            if response.status_code == 200:
                self.credits_info = response.json().get('data', {})
                is_free = self.credits_info.get('is_free_tier', False)
                credits = self.credits_info.get('limit')
                usage = self.credits_info.get('usage', 0)
                rate_limit = self.credits_info.get('rate_limit', {})
                
                # Проверяем лимиты из заголовков
                headers = response.headers
                if 'X-RateLimit-Limit' in headers:
                    limit = headers['X-RateLimit-Limit']
                    remaining = headers['X-RateLimit-Remaining']
                    reset_time = datetime.fromtimestamp(int(headers['X-RateLimit-Reset'])/1000).strftime('%Y-%m-%d %H:%M:%S')
                    self._add_output(
                        f"Model rate limits: {remaining}/{limit} requests remaining, resets at {reset_time}",
                        self.YELLOW
                    )
                    if int(remaining) <= 0:
                        self._add_output(
                            f"Model rate limit reached. Cannot proceed until {reset_time}",
                            self.RED
                        )
                        return None
                
                # Безопасный расчет оставшихся кредитов
                if credits is not None:
                    remaining = credits - usage
                    self._add_output(
                        f"Credits info: {remaining:.1f} credits remaining "
                        f"({rate_limit.get('requests', 'unknown')} requests per {rate_limit.get('interval', 'unknown')})",
                        self.BLUE
                    )
                else:
                    self._add_output(
                        f"Credits info: unlimited credits "
                        f"({rate_limit.get('requests', 'unknown')} requests per {rate_limit.get('interval', 'unknown')})",
                        self.BLUE
                    )
                
                if is_free:
                    self._add_output(
                        "Free tier limits: 20 requests/minute, 200 requests/day",
                        self.YELLOW
                    )
                    
                return self.credits_info
            else:
                self._add_output("Failed to check credits info", self.RED)
                return None
        except Exception as e:
            self._add_output(f"Error checking credits: {str(e)}", self.RED)
            return None

    def _calculate_wait_time(self, response_data: Dict, response_headers: Dict) -> float:
        """Calculates wait time based on rate limits and response headers"""
        # Default wait time
        wait_time = self.retry_delay
        
        if not self.is_openrouter:
            return wait_time
            
        try:
            # Check if we're using a free model
            model = self.settings.model
            is_free_model = model.endswith(':free')
            
            # If we got a 429 (rate limit exceeded)
            if response_data.get('error', {}).get('code') == 429:
                # Try to get reset time from headers
                if 'X-RateLimit-Reset' in response_headers:
                    reset_ms = int(response_headers['X-RateLimit-Reset'])
                    current_ms = int(time.time() * 1000)
                    if reset_ms > current_ms:
                        wait_time = (reset_ms - current_ms) / 1000 + 1
                        
                # For free tier models, use longer delays
                if is_free_model:
                    wait_time = max(wait_time, 5)  # At least 5 seconds for free models
                    
                # Check remaining credits
                if self.credits_info:
                    credits = self.credits_info.get('limit')
                    usage = self.credits_info.get('usage', 0)
                    
                    if credits is not None:  # Если есть лимит кредитов
                        credits_left = credits - usage
                        if credits_left <= 0:
                            self._add_output("No credits remaining!", self.RED)
                            wait_time = max(wait_time, 60)  # Long delay when out of credits
                        elif credits_left < 1:
                            # Less than 1 credit means 1 request per second max
                            wait_time = max(wait_time, 1)
                    # Если credits is None - значит безлимитный аккаунт
                        
            return wait_time
            
        except Exception as e:
            self._add_output(f"Error calculating wait time: {str(e)}", self.RED)
            return self.retry_delay

    def _check_free_model_limits(self) -> tuple[bool, float]:
        """Checks if we've hit free model rate limits.
        Returns: (can_proceed, wait_time_if_needed)
        """
        if not (self.is_openrouter and self.is_free_model):
            return True, 0
            
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400
        
        # Clean up old timestamps
        self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
        self.daily_requests = [t for t in self.daily_requests if t > day_ago]
        
        # Check minute limit
        if len(self.minute_requests) >= 20:
            wait_time = 60 - (now - self.minute_requests[0])
            self._add_output(
                f"Minute limit reached (20/min). Need to wait {int(wait_time)} seconds", 
                self.YELLOW
            )
            return False, wait_time
            
        # Check daily limit
        if len(self.daily_requests) >= 200:
            wait_time = 86400 - (now - self.daily_requests[0])
            self._add_output(
                f"Daily limit reached (200/day). Need to wait {int(wait_time/60)} minutes", 
                self.RED
            )
            return False, wait_time
            
        return True, 0

    def _record_request(self):
        """Records a request timestamp for free model limit tracking"""
        if self.is_openrouter and self.is_free_model:
            now = time.time()
            self.minute_requests.append(now)
            self.daily_requests.append(now)
            self._add_output(
                f"Request recorded ({len(self.minute_requests)}/20 per min, {len(self.daily_requests)}/200 per day)", 
                self.BLUE
            )

    def _format_wait_time(self, seconds: float) -> str:
        """Formats wait time in a human-readable format"""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minutes"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} hours {minutes} minutes"

    def _check_model_limits(self, headers: Dict) -> tuple[bool, float, str]:
        """Checks model-specific rate limits from response headers.
        Returns: (can_proceed, wait_time_if_needed, error_message)
        """
        if not headers:
            return True, 0, ""
            
        try:
            if 'X-RateLimit-Remaining' in headers:
                limit = headers.get('X-RateLimit-Limit', '0')
                remaining = int(headers.get('X-RateLimit-Remaining', '0'))
                reset_ms = int(headers.get('X-RateLimit-Reset', '0'))
                
                if remaining <= 0:
                    current_ms = int(time.time() * 1000)
                    if reset_ms > current_ms:
                        wait_time = (reset_ms - current_ms) / 1000 + 1
                        reset_time = datetime.fromtimestamp(reset_ms/1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                        wait_str = self._format_wait_time(wait_time)
                        error_msg = f"Model rate limit reached ({limit} per day). Will reset at {reset_time} (in {wait_str})"
                        return False, wait_time, error_msg
                        
                self._add_output(
                    f"Model limits: {remaining}/{limit} requests remaining",
                    self.BLUE
                )
                
        except Exception as e:
            self._add_output(f"Error checking model limits: {str(e)}", self.RED)
            
        return True, 0, ""

    def _make_request(self, system_prompt: str, user_prompt: str, current_prompt: str, progress_bar=None) -> Dict:
        """Makes API request with retry mechanism"""
        # Check credits before making requests only for OpenRouter
        if self.is_openrouter and not self.credits_info:
            self._check_credits()
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Define available functions
        functions = [
            {
                "name": "list_tasks",
                "description": "Get list of tasks with optional filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assignee"
                        }
                    }
                }
            },
            {
                "name": "get_task_details",
                "description": "Get task details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "update_task",
                "description": "Update task fields",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status"
                        },
                        "description": {
                            "type": "string",
                            "description": "New description"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "create_task_dependency",
                "description": "Create dependency between tasks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        },
                        "depends_on": {
                            "type": "string",
                            "description": "Dependency task ID"
                        }
                    },
                    "required": ["task_id", "depends_on"]
                }
            },
            {
                "name": "get_task_dependencies",
                "description": "Get task dependencies",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "analyze_critical_path",
                "description": "Analyze project critical path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "find_similar_tasks",
                "description": "Find similar tasks",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results (1-10)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_webpage_content",
                "description": "Get webpage content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Webpage URL"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "list_pages",
                "description": "List project pages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_page_content",
                "description": "Get page content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        }
                    },
                    "required": ["page_id"]
                }
            },
            {
                "name": "get_discussion_comments",
                "description": "Get discussion comments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "discussion_id": {
                            "type": "string",
                            "description": "Discussion ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of comments",
                            "default": 10
                        }
                    },
                    "required": ["discussion_id"]
                }
            }
        ]
        
        data = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "tools": functions,
            "tool_choice": "auto",
            "temperature": 1.21,
            "top_p": 1.0,
            "top_k": 200
        }

        # Log request body
        self._add_output("Request body:", self.BLUE)
        self._add_output(json.dumps(data, indent=2, ensure_ascii=False), self.BLUE)
        
        remaining_retries = self.max_retries
        attempt = 1
        
        while remaining_retries > 0:
            # Check free model limits before making request
            if self.is_openrouter and self.is_free_model:
                can_proceed, wait_time = self._check_free_model_limits()
                if not can_proceed:
                    self._clear_and_print_status(
                        current_prompt,
                        f"{self.YELLOW}Rate limit active. Waiting {int(wait_time)} seconds...{self.ENDC}",
                        "",
                        progress_bar
                    )
                    time.sleep(wait_time)
                    continue
            
            self._add_output(f"Making request (attempt {attempt}/{self.max_retries})...", self.YELLOW)
            self._clear_and_print_status(
                current_prompt,
                f"{self.YELLOW}Making request (attempt {attempt}/{self.max_retries})...{self.ENDC}",
                "",
                progress_bar
            )
            
            try:
                response = requests.post(
                    f"{self.settings.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.settings.request_timeout
                )
                
                response_data = response.json()
                
                # Log response body
                self._add_output("Response body:", self.BLUE)
                self._add_output(json.dumps(response_data, indent=2, ensure_ascii=False), self.BLUE)
                
                # Check model limits if we got a 429
                if response_data.get('error', {}).get('code') == 429:
                    metadata = response_data.get('error', {}).get('metadata', {})
                    can_proceed, wait_time, error_msg = self._check_model_limits(metadata.get('headers', {}))
                    if not can_proceed:
                        # Только одно сообщение в статусе, без дублирования в логе
                        self._clear_and_print_status(
                            current_prompt,
                            f"{self.RED}{error_msg}{self.ENDC}",
                            "",
                            progress_bar
                        )
                        time.sleep(wait_time)
                        continue
                
                # Record request for free model tracking only if successful
                if response.status_code == 200 and "error" not in response_data:
                    self._record_request()
                    self._clear_and_print_status(
                        current_prompt,
                        f"{self.GREEN}✓ Request successful{self.ENDC}",
                        "",
                        progress_bar
                    )
                    return response_data

                # Любая ошибка - пробуем снова
                remaining_retries -= 1
                attempt += 1
                
                # Calculate wait time based on rate limits
                wait_time = self._calculate_wait_time(response_data, response.headers)
                
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                # Только одно сообщение в статусе
                self._clear_and_print_status(
                    current_prompt,
                    f"{self.RED}✗ Request failed (status {response.status_code}). Waiting {self._format_wait_time(wait_time)}{self.ENDC}",
                    error_msg,
                    progress_bar
                )
                
                # Recheck credits after failure only for OpenRouter
                if self.is_openrouter and response.status_code in [402, 429]:  # Payment Required or Rate Limit
                    self._check_credits()
                    
                time.sleep(wait_time)
                continue
                    
            except Exception as e:
                remaining_retries -= 1
                attempt += 1
                # Только одно сообщение в статусе
                self._clear_and_print_status(
                    current_prompt,
                    f"{self.RED}✗ Request failed with error: {str(e)}{self.ENDC}",
                    "",
                    progress_bar
                )
                if remaining_retries > 0:
                    time.sleep(self.retry_delay)
                    continue
        
        # Если дошли сюда - все попытки исчерпаны
        self._clear_and_print_status(
            current_prompt,
            f"{self.RED}✗ All retry attempts exhausted{self.ENDC}",
            "",
            progress_bar
        )
        return None

    def _analyze_function_usage(self, response: Dict) -> Dict:
        """Analyze function calls in the response.
        
        Args:
            response: The API response to analyze
            
        Returns:
            Dict containing analysis results
        """
        analysis = {
            "total_calls": 0,
            "function_calls": [],
            "unique_functions": set(),
            "errors": []
        }
        
        if not response or "choices" not in response:
            return analysis
            
        for choice in response["choices"]:
            if not isinstance(choice, dict) or "message" not in choice:
                continue
                
            message = choice["message"]
            if not isinstance(message, dict):
                continue
                
            # Handle new tool_calls format
            if "tool_calls" in message and message["tool_calls"]:
                for tool_call in message["tool_calls"]:
                    if tool_call.get("type") == "function":
                        analysis["total_calls"] += 1
                        function = tool_call["function"]
                        name = function.get("name", "unknown")
                        arguments = function.get("arguments", "{}")
                        
                        try:
                            parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                        except json.JSONDecodeError:
                            analysis["errors"].append(f"Failed to parse arguments for function {name}")
                            parsed_args = arguments
                        
                        analysis["function_calls"].append({
                            "name": name,
                            "arguments": parsed_args,
                            "id": tool_call.get("id"),
                            "index": tool_call.get("index")
                        })
                        analysis["unique_functions"].add(name)
            
            # Handle legacy function_call format for backward compatibility
            elif "function_call" in message:
                function_call = message["function_call"]
                if isinstance(function_call, dict) and "name" in function_call:
                    analysis["total_calls"] += 1
                    name = function_call["name"]
                    arguments = function_call.get("arguments", "{}")
                    
                    try:
                        parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                    except json.JSONDecodeError:
                        analysis["errors"].append(f"Failed to parse arguments for function {name}")
                        parsed_args = arguments
                    
                    analysis["function_calls"].append({
                        "name": name,
                        "arguments": parsed_args
                    })
                    analysis["unique_functions"].add(name)
        
        analysis["unique_functions"] = list(analysis["unique_functions"])
        return analysis

    def _save_result(
        self,
        hypothesis: Dict,
        system_prompt: str,
        user_prompt: str,
        response: Dict,
        timestamp: str,
    ) -> None:
        """Saves request result to a JSON file"""
        # Analyze function usage if present
        function_analysis = self._analyze_function_usage(response) if response else None
        
        # Update statistics if available
        if self.stats and function_analysis:
            self.stats.add_function_usage(function_analysis)
        
        result = {
            "timestamp": timestamp,
            "hypothesis": hypothesis,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response": response,
            "function_analysis": function_analysis
        }
        
        filename = f"{self.output_dir}/{hypothesis['name']}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def test_hypothesis(self, hypothesis: Dict, user_prompts: Optional[List[str]] = None) -> None:
        """Tests hypothesis with different prompts and collects results"""
        self.current_hypothesis = hypothesis
        
        # Get prompts for testing
        if user_prompts is None:
            from .hypotheses import USER_PROMPTS
            user_prompts = USER_PROMPTS
            
        total_tests = len(hypothesis['system_prompts']) * len(user_prompts)
        
        # Initialize stats for this hypothesis if not already done
        if self.stats:
            self.stats.start_hypothesis(hypothesis, total_tests)
        
        # Предварительная проверка возможности выполнения тестов
        if self.is_openrouter:
            # Проверяем кредиты и лимиты модели
            if not self._check_credits():
                self._add_output("Cannot start tests - rate limits exceeded", self.RED)
                return
            
            if self.is_free_model:
                # Для бесплатной модели проверяем лимиты
                now = time.time()
                minute_ago = now - 60
                day_ago = now - 86400
                
                # Очищаем старые записи
                self.minute_requests = [t for t in self.minute_requests if t > minute_ago]
                self.daily_requests = [t for t in self.daily_requests if t > day_ago]
                
                # Проверяем, сможем ли мы выполнить хотя бы часть тестов
                remaining_minute = 20 - len(self.minute_requests)
                remaining_day = 200 - len(self.daily_requests)
                
                self._add_output(
                    f"Free model limits status: {remaining_minute}/20 requests available per minute, "
                    f"{remaining_day}/200 requests available per day",
                    self.BLUE
                )
                
                if remaining_minute <= 0:
                    wait_time = 60 - (now - self.minute_requests[0])
                    self._add_output(
                        f"Cannot start tests - minute limit reached. Need to wait {int(wait_time)} seconds",
                        self.RED
                    )
                    return
                    
                if remaining_day <= 0:
                    wait_time = 86400 - (now - self.daily_requests[0])
                    self._add_output(
                        f"Cannot start tests - daily limit reached. Need to wait {int(wait_time/60)} minutes",
                        self.RED
                    )
                    return
                    
                if total_tests > remaining_day:
                    self._add_output(
                        f"Warning: Not enough daily capacity for all tests ({total_tests} needed, {remaining_day} available)",
                        self.YELLOW
                    )
            
            # Проверяем кредиты если это не бесплатная модель
            elif self.credits_info:
                credits = self.credits_info.get('limit')
                usage = self.credits_info.get('usage', 0)
                
                if credits is not None:  # Если есть лимит кредитов
                    remaining = credits - usage
                    if remaining <= 0:
                        self._add_output("Cannot start tests - no credits remaining!", self.RED)
                        return
                    elif remaining < total_tests:
                        self._add_output(
                            f"Warning: Not enough credits for all tests ({total_tests} needed, {remaining:.1f} available)",
                            self.YELLOW
                        )
        
        completed_tests = 0
        
        for system_prompt in hypothesis['system_prompts']:
            for user_prompt in user_prompts:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                current_prompt = f"Testing prompt ({completed_tests + 1}/{total_tests}): {user_prompt[:100]}..."
                if self.stats:
                    self.stats.start_prompt(current_prompt)
                
                # Пытаемся получить ответ
                response = self._make_request(system_prompt, user_prompt, current_prompt)
                
                # Если получили успешный ответ - сохраняем
                if response is not None:
                    result_hypothesis = {
                        "name": hypothesis["name"],
                        "description": hypothesis["description"],
                        "system_prompts": [system_prompt]
                    }
                    self._save_result(result_hypothesis, system_prompt, user_prompt, response, timestamp)
                    if self.stats:
                        self.stats.add_success()
                else:
                    if self.stats:
                        self.stats.add_error("max_retries_exceeded")
                
                completed_tests += 1
                if self.stats:
                    self.stats.update_progress()
                
                # Показываем статус перед следующей задержкой
                if completed_tests < total_tests:
                    time.sleep(15)  # Задержка между запросами
        
        if self.stats:
            self.stats.close_progress()
        
        print(f"\nCompleted {completed_tests} tests for hypothesis {hypothesis['name']}")
        print(f"Successfully saved results: {self.stats.hypothesis_stats[hypothesis['name']].successful_requests if self.stats else 'unknown'}")

    def run_all_tests(self) -> None:
        """Runs testing of all hypotheses"""
        from .hypotheses import HYPOTHESES
        
        print("Starting testing of all hypotheses...")
        for hypothesis in HYPOTHESES:
            self.test_hypothesis(hypothesis)
        print("\nTesting completed. Results saved in directory:", self.output_dir) 

    def _get_model_info(self):
        """Get model info for profiling"""
        model = self.settings.model

    def _get_request_data(self, prompt, messages):
        """Get request data for profiling"""
        return {
            "model": self.settings.model,
            "messages": messages,
            "prompt": prompt,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "is_openrouter": self.is_openrouter,
            "is_free_model": self.is_free_model,
            "credits_info": self.credits_info,
            "minute_requests": self.minute_requests,
            "daily_requests": self.daily_requests,
            "api_key": self.api_key,
            "output_dir": self.output_dir,
            "settings": self.settings
        } 