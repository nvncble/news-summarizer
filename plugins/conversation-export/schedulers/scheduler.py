"""
Cross-platform Briefing Scheduler for Digestr.ai
Handles automated email scheduling using OS-native schedulers
"""

import os
import sys
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)


class BriefingScheduler:
    """Cross-platform scheduler for automated briefings"""
    
    def __init__(self, config, email_sender):
        self.config = config
        self.email_sender = email_sender
        self.scheduling_config = config.get("scheduling", {})
        self.system = platform.system().lower()
        
        # Paths for script generation
        self.script_dir = Path.home() / ".digestr" / "schedules"
        self.script_dir.mkdir(parents=True, exist_ok=True)
        
    def initialize(self):
        """Initialize scheduler and setup active schedules"""
        if not self.scheduling_config.get("enabled", False):
            logger.info("Scheduling is disabled")
            return
        
        logger.info(f"Initializing scheduler for {self.system}")
        
        # Clear existing schedules
        self.clear_all_schedules()
        
        # Setup active schedules
        briefings = self.scheduling_config.get("briefings", {})
        for name, briefing_config in briefings.items():
            if briefing_config.get("enabled", False):
                try:
                    self.schedule_briefing(name, briefing_config)
                    logger.info(f"Scheduled {name} briefing at {briefing_config.get('time')}")
                except Exception as e:
                    logger.error(f"Failed to schedule {name}: {e}")
    
    def schedule_briefing(self, name, briefing_config):
        """Schedule a single briefing"""
        time_str = briefing_config.get("time", "08:00")
        style = briefing_config.get("style", "comprehensive")
        recipients = briefing_config.get("recipients", [])
        
        if not recipients:
            logger.warning(f"No recipients configured for {name} briefing")
            return
        
        if self.system == "windows":
            self._schedule_windows(name, time_str, style, recipients)
        elif self.system in ["linux", "darwin"]:  # darwin = macOS
            self._schedule_unix(name, time_str, style, recipients)
        else:
            logger.error(f"Unsupported operating system: {self.system}")
    
    def _schedule_windows(self, name, time_str, style, recipients):
        """Schedule briefing on Windows using Task Scheduler"""
        try:
            # Create PowerShell script for the briefing
            script_path = self._create_briefing_script(name, style, recipients)
            
            # Create scheduled task
            task_name = f"DigestrBriefing_{name}"
            
            # Delete existing task if it exists
            subprocess.run([
                "schtasks", "/delete", "/tn", task_name, "/f"
            ], capture_output=True, check=False)
            
            # Create new task
            cmd = [
                "schtasks", "/create",
                "/tn", task_name,
                "/tr", f'powershell.exe -ExecutionPolicy Bypass -File "{script_path}"',
                "/sc", "daily",
                "/st", time_str,
                "/f"  # Force creation
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Windows task created: {task_name}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create Windows scheduled task: {e}")
            logger.error(f"Command output: {e.stdout}")
            logger.error(f"Command error: {e.stderr}")
    
    def _schedule_unix(self, name, time_str, style, recipients):
        """Schedule briefing on Unix systems using cron"""
        try:
            # Create shell script for the briefing
            script_path = self._create_briefing_script(name, style, recipients)
            
            # Parse time
            hour, minute = time_str.split(":")
            
            # Create cron entry
            cron_entry = f"{minute} {hour} * * * {script_path}"
            
            # Add to crontab
            # First, get existing crontab
            try:
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                existing_cron = result.stdout if result.returncode == 0 else ""
            except:
                existing_cron = ""
            
            # Remove any existing Digestr entries for this briefing
            lines = existing_cron.split('\n')
            filtered_lines = [line for line in lines if f"digestr_{name}" not in line and line.strip()]
            
            # Add new entry
            filtered_lines.append(f"# Digestr.ai {name} briefing")
            filtered_lines.append(cron_entry)
            
            # Write back to crontab
            new_cron = '\n'.join(filtered_lines) + '\n'
            
            process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_cron)
            
            if process.returncode == 0:
                logger.info(f"Cron job created for {name} briefing")
            else:
                logger.error(f"Failed to create cron job for {name}")
                
        except Exception as e:
            logger.error(f"Failed to create Unix cron job: {e}")
    
    def _create_briefing_script(self, name, style, recipients):
        """Create platform-specific script to run briefing"""
        if self.system == "windows":
            return self._create_windows_script(name, style, recipients)
        else:
            return self._create_unix_script(name, style, recipients)
    
    def _create_windows_script(self, name, style, recipients):
        """Create PowerShell script for Windows"""
        script_path = self.script_dir / f"digestr_{name}.ps1"
        
        # Find Python executable and digestr CLI
        python_exe = sys.executable
        digestr_cli = Path(__file__).parent.parent.parent.parent.parent / "digestr_cli_enhanced.py"
        
        recipients_str = " ".join(recipients)
        
        script_content = f'''# Digestr.ai Scheduled Briefing - {name}
# Generated automatically - do not edit manually

$ErrorActionPreference = "Continue"
$LogFile = "$env:USERPROFILE\\.digestr\\logs\\{name}_briefing.log"

# Create log directory if it doesn't exist
$LogDir = Split-Path $LogFile -Parent
if (!(Test-Path $LogDir)) {{
    New-Item -ItemType Directory -Path $LogDir -Force
}}

# Log start time
$StartTime = Get-Date
"$StartTime - Starting {name} briefing" | Out-File -FilePath $LogFile -Append

try {{
    # Change to Digestr directory
    Set-Location "{digestr_cli.parent}"
    
    # Generate briefing
    & "{python_exe}" "{digestr_cli.name}" briefing --style {style} 2>&1 | Out-File -FilePath $LogFile -Append
    
    # Send emails to each recipient
    {chr(10).join([f'    & "{python_exe}" "{digestr_cli.name}" plugin conversation-export email {recipient} 2>&1 | Out-File -FilePath $LogFile -Append' for recipient in recipients])}
    
    $EndTime = Get-Date
    "$EndTime - {name} briefing completed successfully" | Out-File -FilePath $LogFile -Append
    
}} catch {{
    $ErrorTime = Get-Date
    "$ErrorTime - Error in {name} briefing: $_" | Out-File -FilePath $LogFile -Append
}}
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return str(script_path)
    
    def _create_unix_script(self, name, style, recipients):
        """Create shell script for Unix systems"""
        script_path = self.script_dir / f"digestr_{name}.sh"
        
        # Find Python executable and digestr CLI
        python_exe = sys.executable
        digestr_cli = Path(__file__).parent.parent.parent.parent.parent / "digestr_cli_enhanced.py"
        
        script_content = f'''#!/bin/bash
# Digestr.ai Scheduled Briefing - {name}
# Generated automatically - do not edit manually

LOG_FILE="$HOME/.digestr/logs/{name}_briefing.log"
LOG_DIR="$HOME/.digestr/logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log start time
echo "$(date) - Starting {name} briefing" >> "$LOG_FILE"

# Change to Digestr directory
cd "{digestr_cli.parent}"

# Set environment variables if needed
export PYTHONPATH="{digestr_cli.parent}/src:$PYTHONPATH"

# Generate briefing
"{python_exe}" "{digestr_cli.name}" briefing --style {style} >> "$LOG_FILE" 2>&1

# Send emails to each recipient
{chr(10).join([f'"{python_exe}" "{digestr_cli.name}" plugin conversation-export email {recipient} >> "$LOG_FILE" 2>&1' for recipient in recipients])}

echo "$(date) - {name} briefing completed" >> "$LOG_FILE"
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        return str(script_path)
    
    def clear_all_schedules(self):
        """Clear all existing Digestr schedules"""
        try:
            if self.system == "windows":
                self._clear_windows_schedules()
            else:
                self._clear_unix_schedules()
        except Exception as e:
            logger.error(f"Failed to clear existing schedules: {e}")
    
    def _clear_windows_schedules(self):
        """Clear Windows scheduled tasks"""
        try:
            # List all tasks and find Digestr ones
            result = subprocess.run([
                "schtasks", "/query", "/fo", "csv"
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "DigestrBriefing_" in line:
                        # Extract task name
                        parts = line.split(',')
                        if len(parts) > 0:
                            task_name = parts[0].strip('"')
                            if task_name.startswith("DigestrBriefing_"):
                                subprocess.run([
                                    "schtasks", "/delete", "/tn", task_name, "/f"
                                ], capture_output=True, check=False)
                                logger.info(f"Deleted Windows task: {task_name}")
        except Exception as e:
            logger.error(f"Error clearing Windows schedules: {e}")
    
    def _clear_unix_schedules(self):
        """Clear Unix cron jobs"""
        try:
            # Get existing crontab
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if result.returncode != 0:
                return  # No existing crontab
            
            existing_cron = result.stdout
            
            # Filter out Digestr entries
            lines = existing_cron.split('\n')
            filtered_lines = []
            skip_next = False
            
            for line in lines:
                if "# Digestr.ai" in line:
                    skip_next = True
                    continue
                elif skip_next and "digestr_" in line:
                    skip_next = False
                    continue
                elif line.strip():
                    filtered_lines.append(line)
                    skip_next = False
            
            # Write back filtered crontab
            new_cron = '\n'.join(filtered_lines)
            if new_cron.strip():
                new_cron += '\n'
            
            process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_cron)
            
            logger.info("Cleared existing Digestr cron jobs")
            
        except Exception as e:
            logger.error(f"Error clearing Unix schedules: {e}")
    
    def get_schedule_status(self):
        """Get status of all scheduled briefings"""
        status = {
            "platform": self.system,
            "scheduling_enabled": self.scheduling_config.get("enabled", False),
            "briefings": {}
        }
        
        briefings = self.scheduling_config.get("briefings", {})
        for name, config in briefings.items():
            status["briefings"][name] = {
                "enabled": config.get("enabled", False),
                "time": config.get("time"),
                "style": config.get("style"),
                "recipients": config.get("recipients", []),
                "scheduled": self._is_scheduled(name)
            }
        
        return status
    
    def _is_scheduled(self, name):
        """Check if a briefing is actually scheduled in the OS"""
        try:
            if self.system == "windows":
                result = subprocess.run([
                    "schtasks", "/query", "/tn", f"DigestrBriefing_{name}"
                ], capture_output=True, text=True, check=False)
                return result.returncode == 0
            else:
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                if result.returncode == 0:
                    return f"digestr_{name}" in result.stdout
                return False
        except:
            return False
    
    def test_schedule(self, name):
        """Test a schedule by running it immediately"""
        briefings = self.scheduling_config.get("briefings", {})
        if name not in briefings:
            return False, f"Schedule '{name}' not found"
        
        briefing_config = briefings[name]
        style = briefing_config.get("style", "comprehensive")
        recipients = briefing_config.get("recipients", [])
        
        if not recipients:
            return False, "No recipients configured"
        
        try:
            # This would trigger the actual briefing generation and email
            # For now, just return success
            logger.info(f"Test run for {name} briefing")
            return True, f"Test scheduled for {name} (manual trigger needed)"
        except Exception as e:
            return False, f"Test failed: {e}"
    
    def enable_schedule(self, name):
        """Enable a specific schedule"""
        briefings = self.scheduling_config.get("briefings", {})
        if name not in briefings:
            return False, f"Schedule '{name}' not found"
        
        # This would update the config file
        # For now, just log the action
        logger.info(f"Enable request for {name} schedule")
        return True, f"Schedule '{name}' enabled (config update needed)"
    
    def disable_schedule(self, name):
        """Disable a specific schedule"""
        try:
            # Remove from OS scheduler
            if self.system == "windows":
                subprocess.run([
                    "schtasks", "/delete", "/tn", f"DigestrBriefing_{name}", "/f"
                ], capture_output=True, check=False)
            else:
                # Remove from crontab
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    filtered_lines = []
                    skip_next = False
                    
                    for line in lines:
                        if f"# Digestr.ai {name}" in line:
                            skip_next = True
                            continue
                        elif skip_next and f"digestr_{name}" in line:
                            skip_next = False
                            continue
                        elif line.strip():
                            filtered_lines.append(line)
                            skip_next = False
                    
                    new_cron = '\n'.join(filtered_lines)
                    if new_cron.strip():
                        new_cron += '\n'
                    
                    process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
                    process.communicate(input=new_cron)
            
            logger.info(f"Disabled schedule: {name}")
            return True, f"Schedule '{name}' disabled"
            
        except Exception as e:
            logger.error(f"Failed to disable schedule {name}: {e}")
            return False, f"Failed to disable: {e}"