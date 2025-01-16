"""Script to run model profiling tests."""

import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, Set
import frappe
from .profiler import ModelProfiler
from .hypotheses import HYPOTHESES, USER_PROMPTS


@dataclass
class HypothesisStats:
    """Statistics for a single hypothesis"""
    name: str
    description: str
    total_requests: int = 0  # Общее количество запланированных запросов
    completed_requests: int = 0  # Количество выполненных запросов (успешных + неудачных)
    successful_requests: int = 0
    failed_requests: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    total_function_calls: int = 0
    function_calls_by_name: Dict[str, int] = field(default_factory=dict)
    function_errors: Dict[str, int] = field(default_factory=dict)
    unique_functions_used: Set[str] = field(default_factory=set)
    
    # Метрики для оценки гипотез
    avg_functions_per_request: float = 0  # Среднее количество вызовов функций на запрос
    function_diversity_score: float = 0   # Разнообразие используемых функций (уникальные/общие)
    error_rate: float = 0                 # Процент ошибок
    completion_rate: float = 0            # Процент завершенных запросов
    success_rate: float = 0               # Процент успешных запросов
    
    def set_total_requests(self, total: int):
        """Set total number of planned requests"""
        self.total_requests = total
        # Reset counters when setting new total
        self.completed_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.errors_by_type.clear()
        self.total_function_calls = 0
        self.function_calls_by_name.clear()
        self.function_errors.clear()
        self.unique_functions_used.clear()

    def add_error(self, error_type: str):
        """Track error by type"""
        self.failed_requests += 1
        self.completed_requests += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    def add_success(self):
        """Track successful request"""
        self.successful_requests += 1
        self.completed_requests += 1

    def add_function_usage(self, analysis: Dict):
        """Track function usage from analysis"""
        if not analysis:
            return
            
        calls_in_request = analysis.get("total_calls", 0)
        self.total_function_calls += calls_in_request
        
        for call in analysis.get("function_calls", []):
            name = call.get("name")
            if name:
                self.function_calls_by_name[name] = self.function_calls_by_name.get(name, 0) + 1
                self.unique_functions_used.add(name)
        
        for error in analysis.get("errors", []):
            error_type = "parse_error" if "parse" in error.lower() else "other_error"
            self.function_errors[error_type] = self.function_errors.get(error_type, 0) + 1

    def update_metrics(self):
        """Update hypothesis evaluation metrics"""
        # First update completion and success rates
        if self.total_requests > 0:
            self.completion_rate = (self.completed_requests / self.total_requests) * 100
            self.success_rate = (self.successful_requests / self.total_requests) * 100
            
        # Then update error rate based on completed requests
        if self.completed_requests > 0:
            self.avg_functions_per_request = self.total_function_calls / self.completed_requests
            self.error_rate = (self.failed_requests / self.completed_requests) * 100
            
        # Finally update function diversity
        if self.total_function_calls > 0:
            self.function_diversity_score = (len(self.unique_functions_used) / self.total_function_calls) * 100

    def print_summary(self, capture_output: list = None, width: int = 80):
        """Print hypothesis statistics"""
        from .profiler import ModelProfiler

        HEADER = ModelProfiler.HEADER
        BLUE = ModelProfiler.BLUE
        GREEN = ModelProfiler.GREEN
        YELLOW = ModelProfiler.YELLOW
        RED = ModelProfiler.RED
        ENDC = ModelProfiler.ENDC
        BOLD = ModelProfiler.BOLD

        def _add_line(line):
            if capture_output is not None:
                capture_output.append(line)
            else:
                print(line)

        # Update metrics before printing
        self.update_metrics()

        # Format header
        header = f"{'='*width}"
        _add_line(f"{HEADER}{header}{ENDC}")
        
        # Basic info
        _add_line(f"{BOLD}Testing: {self.name}{ENDC}")
        _add_line(f"{BOLD}Description: {self.description}{ENDC}")
        
        # Request stats with color
        color = GREEN if self.success_rate > 80 else (YELLOW if self.success_rate > 50 else RED)
        _add_line(f"\n{color}Request Statistics:{ENDC}")
        _add_line(f"{color}Success Rate: {self.success_rate:>6.1f}% ({self.successful_requests}/{self.total_requests})")
        _add_line(f"Completion Rate: {self.completion_rate:>6.1f}% ({self.completed_requests}/{self.total_requests})")
        _add_line(f"Error Rate: {self.error_rate:>6.1f}% ({self.failed_requests}/{self.completed_requests}){ENDC}")
        
        # Function usage stats
        _add_line(f"\n{BLUE}Function Usage Statistics:{ENDC}")
        _add_line(f"{BLUE}Total Calls: {self.total_function_calls}")
        _add_line(f"Unique Functions: {len(self.unique_functions_used)}")
        _add_line(f"Avg Calls per Request: {self.avg_functions_per_request:.2f}")
        _add_line(f"Function Diversity Score: {self.function_diversity_score:.1f}%{ENDC}")
        
        # Function usage bars
        if self.function_calls_by_name:
            _add_line(f"\n{BLUE}Function Usage Distribution:{ENDC}")
            max_count = max(self.function_calls_by_name.values())
            bar_width = (width - 30)
            for name, count in sorted(self.function_calls_by_name.items(), key=lambda x: x[1], reverse=True):
                usage_percent = count / self.total_function_calls * 100
                bar_length = int(bar_width * count / max_count)
                bar = "█" * bar_length + "░" * (bar_width - bar_length)
                _add_line(f"{BLUE}{name[:15]:<15} {count:>3} ({usage_percent:>5.1f}%) {bar}{ENDC}")
        
        # Errors if any
        if self.errors_by_type:
            _add_line(f"\n{RED}Error Types:{ENDC}")
            for error_type, count in self.errors_by_type.items():
                _add_line(f"{RED}{error_type}: {count}{ENDC}")
                
        _add_line(f"{HEADER}{header}{ENDC}\n")


@dataclass
class TestStats:
    """Statistics for test execution"""
    hypothesis_stats: Dict[str, HypothesisStats] = field(default_factory=dict)
    current_hypothesis: str = None
    current_prompt: str = None
    progress_bar = None  # Added field for progress bar
    
    def start_hypothesis(self, hypothesis: Dict, total_tests: int = None):
        """Start tracking new hypothesis"""
        self.current_hypothesis = hypothesis["name"]
        if self.current_hypothesis not in self.hypothesis_stats:
            stats = HypothesisStats(
                name=hypothesis["name"],
                description=hypothesis["description"]
            )
            if total_tests:
                stats.set_total_requests(total_tests)
            self.hypothesis_stats[self.current_hypothesis] = stats
            
        # Initialize progress bar if total_tests provided
        if total_tests:
            from tqdm import tqdm
            self.progress_bar = tqdm(total=total_tests, desc="Progress", leave=True)
        # Print initial stats when starting hypothesis
        self._print_current_stats()

    def update_progress(self):
        """Update progress bar"""
        if self.progress_bar:
            self.progress_bar.update(1)

    def _print_current_stats(self):
        """Print current hypothesis statistics"""
        if self.current_hypothesis:
            # Save progress bar position
            if self.progress_bar:
                self.progress_bar.clear()
            
            # Get terminal size
            terminal_width = shutil.get_terminal_size().columns
            terminal_height = shutil.get_terminal_size().lines
            
            # Clear screen
            print("\033[2J\033[H", end="")
            
            # Calculate available space
            stats_lines = 6  # Basic stats lines (headers, separators, etc.)
            hypothesis_lines = len(self.hypothesis_stats) * 1  # One line per hypothesis
            current_info_lines = 15  # Current hypothesis info + metrics
            progress_bar_lines = 2  # Space for progress bar
            
            # Calculate space for logs
            available_log_lines = terminal_height - (stats_lines + hypothesis_lines + current_info_lines + progress_bar_lines)
            
            # Get logs from ModelProfiler (last N lines based on available space)
            from .profiler import ModelProfiler
            output_lines = ModelProfiler.get_output_lines()[-available_log_lines:] if available_log_lines > 0 else []
            
            # Print logs first (they will scroll up)
            for line in output_lines:
                print(line)
            
            # Print separator (changed to blue)
            print(f"\033[94m{'='*terminal_width}\033[0m")
            
            # Print statistics for all hypotheses
            print("\033[94mStatistics for all hypotheses:\033[0m")
            for name, stats in self.hypothesis_stats.items():
                stats.update_metrics()  # Update metrics before printing
                marker = "→ " if name == self.current_hypothesis else "  "
                # Use yellow for low success rates instead of red
                color = "\033[92m" if stats.success_rate > 80 else "\033[93m"
                print(f"{marker}{color}{name:<20} | "
                      f"Success: {stats.successful_requests:>2}/{stats.total_requests:<2} ({stats.success_rate:>5.1f}%) | "
                      f"Progress: {stats.completed_requests:>2}/{stats.total_requests:<2} ({stats.completion_rate:>5.1f}%) | "
                      f"Funcs: {stats.total_function_calls:>2} ({len(stats.unique_functions_used)} unique)\033[0m")
            
            # Print separator (changed to blue)
            print(f"\033[94m{'='*terminal_width}\033[0m")
            
            # Print current hypothesis details with metrics
            stats = self.hypothesis_stats[self.current_hypothesis]
            stats.update_metrics()
            
            print(f"\033[1mTesting hypothesis: {self.current_hypothesis}")
            print(f"Description: {stats.description}\033[0m")
            
            # Print metrics for current hypothesis (using yellow instead of red)
            color = "\033[92m" if stats.success_rate > 80 else "\033[93m"
            print(f"\n{color}Request Statistics:")
            print(f"Success Rate: {stats.success_rate:>6.1f}% ({stats.successful_requests}/{stats.total_requests})")
            print(f"Completion Rate: {stats.completion_rate:>6.1f}% ({stats.completed_requests}/{stats.total_requests})")
            if stats.completed_requests > 0:
                error_color = "\033[91m" if stats.error_rate > 50 else "\033[93m"
                print(f"Error Rate: {error_color}{stats.error_rate:>6.1f}% ({stats.failed_requests}/{stats.completed_requests})\033[0m")
            else:
                print(f"Error Rate: {stats.error_rate:>6.1f}% ({stats.failed_requests}/{stats.completed_requests})\033[0m")
            
            print(f"\n\033[94mFunction Usage:")
            print(f"Total Calls: {stats.total_function_calls}")
            print(f"Unique Functions: {len(stats.unique_functions_used)}")
            print(f"Avg Calls per Request: {stats.avg_functions_per_request:.2f}")
            print(f"Function Diversity Score: {stats.function_diversity_score:.1f}%\033[0m")
            
            if self.current_prompt:
                print(f"\n\033[1mCurrent: {self.current_prompt}\033[0m")
            
            # Move cursor to preserve space for progress bar
            if self.progress_bar:
                print("\n" * (progress_bar_lines - 1))
                # Move cursor up to where progress bar should be
                print(f"\033[{progress_bar_lines}A", end="")
                self.progress_bar.refresh()

    def close_progress(self):
        """Close progress bar"""
        if self.progress_bar:
            self.progress_bar.close()
            self.progress_bar = None

    def add_error(self, error_type: str):
        """Track error by type"""
        if self.current_hypothesis:
            self.hypothesis_stats[self.current_hypothesis].add_error(error_type)
            # Print updated stats after error
            self._print_current_stats()

    def add_success(self):
        """Track successful request"""
        if self.current_hypothesis:
            self.hypothesis_stats[self.current_hypothesis].add_success()
            # Print updated stats after success
            self._print_current_stats()

    def add_function_usage(self, analysis: Dict):
        """Track function usage from analysis"""
        if self.current_hypothesis:
            self.hypothesis_stats[self.current_hypothesis].add_function_usage(analysis)
            # Print updated stats after each function usage
            self._print_current_stats()

    def start_prompt(self, prompt: str):
        """Track current prompt being tested"""
        self.current_prompt = prompt
        self._print_current_stats()

    def print_summary(self):
        """Print complete test execution summary"""
        print("\nComplete Test Execution Summary:")
        for hypothesis in self.hypothesis_stats.values():
            hypothesis.print_summary()
            print("\n" + "="*80)


def run():
    """Run model profiling with defined hypotheses."""
    output_dir = "model_profiling_results"
    stats = TestStats()
    
    # Clean up old results
    results_path = os.path.join(frappe.get_site_path(), output_dir)
    if os.path.exists(results_path):
        print(f"Cleaning up old results in {results_path}")
        shutil.rmtree(results_path)
        os.makedirs(results_path)
    
    profiler = ModelProfiler(output_dir=output_dir, stats=stats)
    
    # Initialize stats for all hypotheses with correct total_tests
    for hypothesis in HYPOTHESES:
        total_tests = len(hypothesis['system_prompts']) * len(USER_PROMPTS)
        stats.start_hypothesis(hypothesis, total_tests)
    
    # Test each hypothesis
    for hypothesis in HYPOTHESES:
        # Create a copy of hypothesis without modifying the original
        test_hypothesis = hypothesis.copy()
        # Pass prompts separately
        profiler.test_hypothesis(test_hypothesis, USER_PROMPTS)
    
    # Print final statistics
    stats.print_summary()

if __name__ == "__main__":
    run() 