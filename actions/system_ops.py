"""
AEGIS System Telemetry & Operations
Safe read-only diagnostics for CPU, Memory, Storage, Battery, OS, and Processes.
"""

import time
import platform
import psutil
from typing import Dict, Any, List

class SystemInspector:
    """Provides non-destructive, real-time operating system telemetry."""

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Collects current system performance statistics."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)

        # Virtual Memory
        mem = psutil.virtual_memory()
        mem_total_gb = round(mem.total / (1024 ** 3), 2)
        mem_used_gb = round(mem.used / (1024 ** 3), 2)
        mem_percent = mem.percent

        # Disk
        disk = psutil.disk_usage("/")
        disk_total_gb = round(disk.total / (1024 ** 3), 2)
        disk_used_gb = round(disk.used / (1024 ** 3), 2)
        disk_percent = disk.percent

        # Battery
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 100
        power_plugged = battery.power_plugged if battery else True

        # OS Details
        os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
        uptime_hours = round((time.time() - psutil.boot_time()) / 3600, 1)

        return {
            "os": os_name,
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_count,
            "memory_total_gb": mem_total_gb,
            "memory_used_gb": mem_used_gb,
            "memory_percent": mem_percent,
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_percent": disk_percent,
            "battery_percent": battery_percent,
            "power_plugged": power_plugged,
            "uptime_hours": uptime_hours
        }

    @staticmethod
    def get_top_processes(limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top processes sorted by memory usage."""
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
            try:
                info = p.info
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "memory_percent": round(info['memory_percent'] or 0, 1),
                    "cpu_percent": round(info['cpu_percent'] or 0, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: x["memory_percent"], reverse=True)
        return procs[:limit]

    @staticmethod
    def lock_screen() -> Dict[str, Any]:
        """Locks the Windows workstation."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "message": "Screen locked successfully."}
        except Exception as e:
            return {"success": False, "message": f"Failed to lock screen: {e}"}

    @staticmethod
    def sleep_pc() -> Dict[str, Any]:
        """Puts the PC into sleep/suspend mode."""
        import subprocess
        try:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
                check=True
            )
            return {"success": True, "message": "PC is entering sleep mode."}
        except Exception as e:
            return {"success": False, "message": f"Failed to sleep PC: {e}"}
