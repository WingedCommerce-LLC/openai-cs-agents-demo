#!/usr/bin/env python3

"""
OpenAI Agents Enterprise Demo - Scenario Runner
Version: 1.0.0
Description: Automated demo scenario execution and management
"""

import json
import time
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from colorama import init, Fore, Style
    init()  # Initialize colorama for cross-platform colored output
except ImportError:
    print("Installing required dependencies...")
    os.system("pip install requests colorama")
    import requests
    from colorama import init, Fore, Style
    init()


class DemoStatus(Enum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DemoStep:
    step: int
    title: str
    description: str
    user_input: Optional[str] = None
    expected_agent: Optional[str] = None
    expected_handoff: Optional[str] = None
    expected_tool: Optional[str] = None
    action_type: Optional[str] = None
    demo_notes: str = ""


@dataclass
class DemoScenario:
    id: str
    name: str
    description: str
    duration_minutes: int
    difficulty: str
    tags: List[str]
    steps: List[DemoStep]
    success_criteria: List[str]


class DemoRunner:
    def __init__(self, backend_url: str = "http://localhost:8000",
                 frontend_url: str = "http://localhost:3000"):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.scenarios: Dict[str, DemoScenario] = {}
        self.current_scenario: Optional[str] = None
        self.current_step: int = 0
        self.status = DemoStatus.READY
        self.conversation_id: Optional[str] = None
        self.step_delay = 2.0
        self.auto_advance = False
        self.verbose = False

        # Load scenarios
        self._load_scenarios()

    def _load_scenarios(self):
        """Load demo scenarios from JSON file"""
        scenarios_file = Path(__file__).parent.parent / "scenarios" / "demo-flows.json"

        try:
            with open(scenarios_file, 'r') as f:
                data = json.load(f)

            for scenario_id, scenario_data in data.get("demo_scenarios", {}).items():
                steps = [
                    DemoStep(
                        step=step_data["step"],
                        title=step_data["title"],
                        description=step_data["description"],
                        user_input=step_data.get("user_input"),
                        expected_agent=step_data.get("expected_agent"),
                        expected_handoff=step_data.get("expected_handoff"),
                        expected_tool=step_data.get("expected_tool"),
                        action_type=step_data.get("action_type"),
                        demo_notes=step_data.get("demo_notes", "")
                    )
                    for step_data in scenario_data["steps"]
                ]

                self.scenarios[scenario_id] = DemoScenario(
                    id=scenario_data["id"],
                    name=scenario_data["name"],
                    description=scenario_data["description"],
                    duration_minutes=scenario_data["duration_minutes"],
                    difficulty=scenario_data["difficulty"],
                    tags=scenario_data["tags"],
                    steps=steps,
                    success_criteria=scenario_data["success_criteria"]
                )

            self.print_success(f"Loaded {len(self.scenarios)} demo scenarios")

        except FileNotFoundError:
            self.print_error(f"Scenarios file not found: {scenarios_file}")
        except json.JSONDecodeError as e:
            self.print_error(f"Invalid JSON in scenarios file: {e}")
        except Exception as e:
            self.print_error(f"Error loading scenarios: {e}")

    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{text.center(80)}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*80}{Style.RESET_ALL}\n")

    def print_section(self, text: str):
        """Print a section header"""
        print(f"\n{Fore.CYAN}▶ {text}{Style.RESET_ALL}")

    def print_step(self, text: str):
        """Print a step"""
        print(f"  {Fore.BLUE}• {text}{Style.RESET_ALL}")

    def print_success(self, text: str):
        """Print success message"""
        print(f"  {Fore.GREEN}✓ {text}{Style.RESET_ALL}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"  {Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"  {Fore.RED}✗ {text}{Style.RESET_ALL}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"  {Fore.WHITE}ℹ {text}{Style.RESET_ALL}")

    def check_services(self) -> bool:
        """Check if backend and frontend services are running"""
        self.print_section("Checking Services")

        # Check backend
        try:
            response = requests.get(f"{self.backend_url}/", timeout=5)
            if response.status_code == 200:
                self.print_success("Backend service is running")
                backend_ok = True
            else:
                self.print_error(f"Backend returned status {response.status_code}")
                backend_ok = False
        except requests.RequestException as e:
            self.print_error(f"Backend service not accessible: {e}")
            backend_ok = False

        # Check frontend
        try:
            response = requests.get(f"{self.frontend_url}/", timeout=5)
            if response.status_code == 200:
                self.print_success("Frontend service is running")
                frontend_ok = True
            else:
                self.print_error(f"Frontend returned status {response.status_code}")
                frontend_ok = False
        except requests.RequestException as e:
            self.print_error(f"Frontend service not accessible: {e}")
            frontend_ok = False

        return backend_ok and frontend_ok

    def list_scenarios(self):
        """List all available scenarios"""
        self.print_section("Available Demo Scenarios")

        for scenario_id, scenario in self.scenarios.items():
            difficulty_color = {
                'beginner': Fore.GREEN,
                'intermediate': Fore.YELLOW,
                'advanced': Fore.RED
            }.get(scenario.difficulty, Fore.WHITE)

            print(f"\n  {Fore.CYAN}{scenario.name}{Style.RESET_ALL}")
            print(f"    ID: {scenario_id}")
            print(f"    Description: {scenario.description}")
            print(f"    Duration: {scenario.duration_minutes} minutes")
            print(f"    Difficulty: {difficulty_color}{scenario.difficulty}"
                  f"{Style.RESET_ALL}")
            print(f"    Tags: {', '.join(scenario.tags)}")
            print(f"    Steps: {len(scenario.steps)}")

    def load_scenario(self, scenario_id: str) -> bool:
        """Load a specific scenario"""
        if scenario_id not in self.scenarios:
            self.print_error(f"Scenario '{scenario_id}' not found")
            return False

        self.current_scenario = scenario_id
        self.current_step = 0
        self.status = DemoStatus.READY
        self.conversation_id = None

        scenario = self.scenarios[scenario_id]
        self.print_success(f"Loaded scenario: {scenario.name}")
        self.print_info(f"Description: {scenario.description}")
        self.print_info(f"Steps: {len(scenario.steps)}")

        return True

    def execute_step(self, step: DemoStep) -> bool:
        """Execute a single demo step"""
        self.print_section(f"Step {step.step}: {step.title}")
        self.print_info(step.description)

        if step.demo_notes and self.verbose:
            self.print_info(f"Notes: {step.demo_notes}")

        # Handle different action types
        if step.action_type == "cli_command":
            return self._execute_cli_command(step)
        elif step.action_type == "ui_navigation":
            return self._execute_ui_navigation(step)
        elif step.action_type == "file_upload":
            return self._execute_file_upload(step)
        elif step.user_input:
            return self._execute_chat_interaction(step)
        else:
            self.print_info("Manual step - press Enter to continue")
            input()
            return True

    def _execute_chat_interaction(self, step: DemoStep) -> bool:
        """Execute a chat interaction step"""
        if not step.user_input:
            return True

        self.print_step(f"Sending message: '{step.user_input}'")

        try:
            # Send message to backend
            payload = {
                "message": step.user_input
            }

            if self.conversation_id:
                payload["conversation_id"] = self.conversation_id

            response = requests.post(
                f"{self.backend_url}/chat",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Extract conversation ID for future requests
                if not self.conversation_id and "conversation_id" in data:
                    self.conversation_id = data["conversation_id"]

                # Check agent routing
                if step.expected_agent and "events" in data:
                    agent_events = [e for e in data["events"]
                                    if e.get("type") == "agent_message"]
                    if agent_events:
                        current_agent = agent_events[-1].get("agent", "unknown")
                        if current_agent == step.expected_agent:
                            self.print_success(f"Correct agent: {current_agent}")
                        else:
                            self.print_warning(
                                f"Expected {step.expected_agent}, "
                                f"got {current_agent}")

                # Check handoffs
                if step.expected_handoff and "events" in data:
                    handoff_events = [e for e in data["events"]
                                      if e.get("type") == "handoff"]
                    if handoff_events:
                        handoff_target = handoff_events[-1].get(
                            "target_agent", "unknown")
                        if handoff_target == step.expected_handoff:
                            self.print_success(
                                f"Correct handoff: {handoff_target}")
                        else:
                            self.print_warning(
                                f"Expected handoff to "
                                f"{step.expected_handoff}, "
                                f"got {handoff_target}")

                # Check tool execution
                if step.expected_tool and "events" in data:
                    tool_events = [e for e in data["events"]
                                   if e.get("type") == "tool_call"]
                    if tool_events:
                        tool_name = tool_events[-1].get("tool_name", "unknown")
                        if tool_name == step.expected_tool:
                            self.print_success(
                                f"Correct tool executed: {tool_name}")
                        else:
                            self.print_warning(
                                f"Expected tool {step.expected_tool}, "
                                f"got {tool_name}")

                # Display response
                if "messages" in data and data["messages"]:
                    last_message = data["messages"][-1]
                    if last_message.get("role") == "assistant":
                        self.print_success("Agent response received")
                        if self.verbose:
                            content = last_message.get('content', '')[:100]
                            print(f"    Response: {content}...")

                return True
            else:
                self.print_error(f"Chat request failed: {response.status_code}")
                return False

        except requests.RequestException as e:
            self.print_error(f"Chat request error: {e}")
            return False

    def _execute_cli_command(self, step: DemoStep) -> bool:
        """Execute a CLI command step"""
        # This would execute CLI commands - placeholder for now
        self.print_step("CLI command execution (simulated)")
        return True

    def _execute_ui_navigation(self, step: DemoStep) -> bool:
        """Execute UI navigation step"""
        # This would control UI navigation - placeholder for now
        self.print_step("UI navigation (simulated)")
        return True

    def _execute_file_upload(self, step: DemoStep) -> bool:
        """Execute file upload step"""
        # This would handle file uploads - placeholder for now
        self.print_step("File upload (simulated)")
        return True

    def run_scenario(self, scenario_id: str, auto_advance: bool = False) -> bool:
        """Run a complete scenario"""
        if not self.load_scenario(scenario_id):
            return False

        scenario = self.scenarios[scenario_id]
        self.auto_advance = auto_advance
        self.status = DemoStatus.RUNNING

        self.print_header(f"Running Demo Scenario: {scenario.name}")

        success_count = 0
        total_steps = len(scenario.steps)

        for i, step in enumerate(scenario.steps, 1):
            self.current_step = i

            if self.execute_step(step):
                success_count += 1

            # Wait between steps
            if i < total_steps:
                if self.auto_advance:
                    self.print_info(f"Waiting {self.step_delay} seconds...")
                    time.sleep(self.step_delay)
                else:
                    self.print_info("Press Enter to continue to next step...")
                    input()

        # Summary
        self.print_section("Demo Scenario Complete")
        self.print_info(f"Steps completed: {success_count}/{total_steps}")

        if success_count == total_steps:
            self.print_success("All steps completed successfully!")
            self.status = DemoStatus.COMPLETED
            return True
        else:
            failed_steps = total_steps - success_count
            self.print_warning(f"{failed_steps} steps had issues")
            self.status = DemoStatus.FAILED
            return False

    def interactive_mode(self):
        """Run in interactive mode"""
        self.print_header("OpenAI Agents Enterprise Demo - Interactive Mode")

        while True:
            print(f"\n{Fore.CYAN}Demo Runner Commands:{Style.RESET_ALL}")
            print("  list     - List available scenarios")
            print("  run      - Run a scenario")
            print("  check    - Check service status")
            print("  status   - Show current status")
            print("  quit     - Exit")

            try:
                command = input(
                    f"\n{Fore.YELLOW}demo>{Style.RESET_ALL}").strip().lower()

                if command == "quit" or command == "exit":
                    break
                elif command == "list":
                    self.list_scenarios()
                elif command == "check":
                    self.check_services()
                elif command == "status":
                    self._show_status()
                elif command == "run":
                    self._interactive_run()
                else:
                    self.print_error(f"Unknown command: {command}")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
                break
            except EOFError:
                break

    def _show_status(self):
        """Show current demo status"""
        self.print_section("Demo Status")
        self.print_info(f"Status: {self.status.value}")
        self.print_info(
            f"Current scenario: {self.current_scenario or 'None'}")
        self.print_info(f"Current step: {self.current_step}")
        self.print_info(f"Conversation ID: {self.conversation_id or 'None'}")

    def _interactive_run(self):
        """Interactive scenario selection and execution"""
        self.list_scenarios()

        scenario_id = input(
            f"\n{Fore.YELLOW}Enter scenario ID: {Style.RESET_ALL}").strip()

        if scenario_id not in self.scenarios:
            self.print_error(f"Scenario '{scenario_id}' not found")
            return

        auto_advance = input(
            f"{Fore.YELLOW}Auto-advance steps? (y/N): {Style.RESET_ALL}"
        ).strip().lower() == 'y'

        self.run_scenario(scenario_id, auto_advance)


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI Agents Enterprise Demo Runner")
    parser.add_argument("--scenario", "-s", help="Scenario ID to run")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available scenarios")
    parser.add_argument("--check", "-c", action="store_true",
                        help="Check service status")
    parser.add_argument("--auto-advance", "-a", action="store_true",
                        help="Auto-advance through steps")
    parser.add_argument("--step-delay", "-d", type=float, default=2.0,
                        help="Delay between steps (seconds)")
    parser.add_argument("--backend-url", default="http://localhost:8000",
                        help="Backend URL")
    parser.add_argument("--frontend-url", default="http://localhost:3000",
                        help="Frontend URL")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    # Create demo runner
    runner = DemoRunner(args.backend_url, args.frontend_url)
    runner.step_delay = args.step_delay
    runner.verbose = args.verbose

    if args.list:
        runner.list_scenarios()
    elif args.check:
        runner.check_services()
    elif args.scenario:
        if not runner.check_services():
            print(f"{Fore.RED}Services not ready. Please start the demo "
                  f"environment first.{Style.RESET_ALL}")
            sys.exit(1)

        success = runner.run_scenario(args.scenario, args.auto_advance)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        runner.interactive_mode()


if __name__ == "__main__":
    main()
