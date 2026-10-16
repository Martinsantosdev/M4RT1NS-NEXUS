#!/usr/bin/env python3
# M4RT1NS.exe NEXUS 8.0
# Python standard library only; no root required.

import os
import sys
import json
import time
import shutil
import socket
import hashlib
import platform
import subprocess
from datetime import datetime

APP = "M4RT1NS.exe"
VERSION = "NEXUS 8.0"
BASE = os.path.abspath(os.path.dirname(__file__))
VAULT = os.path.join(BASE, "reports")

G = "\033[92m"
C = "\033[96m"
P = "\033[95m"
Y = "\033[93m"
RED = "\033[91m"
W = "\033[97m"
D = "\033[90m"
B = "\033[1m"
R = "\033[0m"


# -------------------- CORE UTILITIES --------------------

def clear():
    os.system("clear" if os.name == "posix" else "cls")


def terminal_width():
    try:
        return max(42, min(shutil.get_terminal_size().columns, 90))
    except Exception:
        return 60


def command(args, timeout=5):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=timeout, errors="replace"
        )
        return (result.stdout or result.stderr).strip()
    except Exception:
        return ""


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except (OSError, ValueError):
        return ""


def prop(key):
    if shutil.which("getprop"):
        return command(["getprop", key])
    return ""


def fmt_bytes(value):
    try:
        value = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return "{:.1f} {}".format(value, unit)
            value /= 1024
    except (TypeError, ValueError):
        pass
    return "N/A"


def fmt_time(seconds):
    if seconds is None:
        return "N/A"
    try:
        seconds = max(0, int(float(seconds)))
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return "{}d {:02}h {:02}m {:02}s".format(
            days, hours, minutes, seconds
        )
    except (TypeError, ValueError):
        return "N/A"


def uptime():
    try:
        return float(read_text("/proc/uptime").split()[0])
    except (ValueError, IndexError):
        return None


def ram_data():
    data = {}
    for row in read_text("/proc/meminfo").splitlines():
        parts = row.replace(":", "").split()
        if len(parts) >= 2:
            try:
                data[parts[0]] = int(parts[1]) * 1024
            except ValueError:
                pass

    total = data.get("MemTotal", 0)
    available = data.get("MemAvailable", data.get("MemFree", 0))
    used = max(0, total - available)
    percent = round(used * 100 / total, 1) if total else None

    return {
        "total_bytes": total,
        "used_bytes": used,
        "available_bytes": available,
        "percent": percent
    }


def bar(percent, length=20):
    if percent is None:
        return D + "░" * length + R + " N/A"

    percent = max(0, min(100, float(percent)))
    filled = int(length * percent / 100)
    color = G if percent < 70 else Y if percent < 90 else RED
    return (
        color + "█" * filled + D + "░" * (length - filled)
        + R + " {:g}%".format(percent)
    )


def frame(title, rows, color=C):
    width = terminal_width()
    inside = width - 4

    print(color + "╭" + "─" * (width - 2) + "╮" + R)
    print(color + "│" + R + B + (" " + title)[:inside].ljust(inside)
          + R + color + "│" + R)
    print(color + "├" + "─" * (width - 2) + "┤" + R)

    for row in rows:
        text = str(row)
        # Keep terminal output readable on narrow screens.
        import re
        visible = re.sub(r"\033\[[0-9;]*m", "", text)
        visible = visible[:inside]
        padding = max(0, inside - len(visible))
        print(color + "│" + R + " " + text + " " * padding
              + color + "│" + R)

    print(color + "╰" + "─" * (width - 2) + "╯" + R)


def header():
    width = terminal_width()
    print(G + "╔" + "═" * (width - 2) + "╗" + R)
    print(G + "║" + R + C + B +
          "  M4RT1NS.exe // NEXUS 8.0".ljust(width - 3)
          + R + G + "║" + R)
    print(G + "║" + R + W +
          "  ADVANCED ANDROID CONTROL CENTER".ljust(width - 3)
          + R + G + "║" + R)
    print(G + "╚" + "═" * (width - 2) + "╝" + R)
    print(D + " " + datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
          + "  |  PYTHON STANDARD LIBRARY" + R)


def pause():
    input("\n" + G + "  ENTER" + R + " para voltar...")


def ask_path(prompt, default=None):
    hint = " [" + default + "]" if default else ""
    raw = input("  " + C + prompt + R + hint + ": ").strip()
    path = raw or default
    if not path:
        return None
    return os.path.abspath(os.path.expanduser(path))


def safe_walk(root):
    """Walk without following directory symlinks; skip inaccessible paths."""
    def onerror(_error):
        pass

    for current, dirs, files in os.walk(
        root, topdown=True, onerror=onerror, followlinks=False
    ):
        dirs[:] = [
            d for d in dirs
            if not os.path.islink(os.path.join(current, d))
        ]
        yield current, dirs, files


# -------------------- DEVICE INFORMATION --------------------

def device_info():
    return {
        "manufacturer": prop("ro.product.manufacturer") or "Unavailable",
        "model": prop("ro.product.model") or platform.node() or "Unavailable",
        "device": prop("ro.product.device") or "Unavailable",
        "android_version": prop("ro.build.version.release") or "Unavailable",
        "android_api": prop("ro.build.version.sdk") or "Unavailable",
        "build": prop("ro.build.display.id") or "Unavailable",
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "platform": platform.platform()
    }


def storage_info(path="/data"):
    return command(["df", "-h", path]) or "Storage details unavailable."


def device_center():
    clear()
    header()
    info = device_info()

    frame("DEVICE IDENTITY", [
        "Manufacturer : " + info["manufacturer"],
        "Model        : " + info["model"],
        "Device       : " + info["device"],
        "Android      : " + info["android_version"],
        "API level    : " + info["android_api"],
        "Architecture : " + info["architecture"],
        "Python       : " + info["python_version"],
        "Build        : " + info["build"]
    ], C)

    ram = ram_data()
    frame("MEMORY", [
        "RAM usage    : " + bar(ram["percent"]),
        "Used         : " + fmt_bytes(ram["used_bytes"]),
        "Available    : " + fmt_bytes(ram["available_bytes"]),
        "Total        : " + fmt_bytes(ram["total_bytes"])
    ], P)

    frame("STORAGE", [storage_info()], Y)
    pause()


# -------------------- PERFORMANCE RADAR --------------------

def process_snapshot():
    processes = []
    proc_root = "/proc"

    try:
        names = os.listdir(proc_root)
    except OSError:
        return processes

    for name in names:
        if not name.isdigit():
            continue

        pid = int(name)
        status = read_text(os.path.join(proc_root, name, "status"))
        cmdline = read_text(os.path.join(proc_root, name, "cmdline"))
        if not cmdline:
            cmdline = read_text(os.path.join(proc_root, name, "comm"))

        rss = 0
        for row in status.splitlines():
            if row.startswith("VmRSS:"):
                parts = row.split()
                if len(parts) >= 2:
                    try:
                        rss = int(parts[1]) * 1024
                    except ValueError:
                        pass
                break

        if not cmdline:
            for row in status.splitlines():
                if row.startswith("Name:"):
                    cmdline = row.split(":", 1)[-1].strip()
                    break

        processes.append({
            "pid": pid,
            "name": cmdline.replace("\x00", " ")[:70] or "unknown",
            "rss_bytes": rss
        })

    processes.sort(key=lambda p: p["rss_bytes"], reverse=True)
    return processes


def load_average():
    raw = read_text("/proc/loadavg")
    if raw:
        return " ".join(raw.split()[:3])
    return "Unavailable"


def performance_radar():
    try:
        while True:
            clear()
            header()

            ram = ram_data()
            up = uptime()
            processes = process_snapshot()

            frame("PERFORMANCE RADAR", [
                "RAM          " + bar(ram["percent"]),
                "RAM used     " + fmt_bytes(ram["used_bytes"]),
                "RAM total    " + fmt_bytes(ram["total_bytes"]),
                "System uptime: " + fmt_time(up),
                "Load average : " + load_average(),
                "Visible proc : " + str(len(processes))
            ], G)

            rows = []
            for proc in processes[:8]:
                rows.append(
                    "PID {:>6} | {:<22} | {}".format(
                        proc["pid"],
                        proc["name"][:22],
                        fmt_bytes(proc["rss_bytes"])
                    )
                )

            if not rows:
                rows = ["Process information unavailable."]

            frame("TOP PROCESSES BY RESIDENT MEMORY", rows, C)
            print("\n" + D + "Atualiza a cada 3 segundos. Ctrl+C volta ao menu."
                  + R)
            time.sleep(3)

    except KeyboardInterrupt:
        pass


# -------------------- LARGE FILE FINDER --------------------

def large_file_finder():
    clear()
    header()
    frame("LARGE FILE DETECTOR", [
        "Busca somente arquivos; nada será apagado.",
        "Escolha uma pasta que você tenha permissão para ler."
    ], Y)

    root = ask_path("Pasta para pesquisar", "~")
    if not root or not os.path.isdir(root):
        print(RED + "  Pasta inválida ou inacessível." + R)
        pause()
        return

    raw = input("  Tamanho mínimo em MB [100]: ").strip()
    try:
        min_bytes = max(1, float(raw or "100")) * 1024 * 1024
    except ValueError:
        print(RED + "  Tamanho inválido." + R)
        pause()
        return

    print("\n  Pesquisando... isso pode levar algum tempo.")
    found = []
    examined = 0

    for current, _dirs, files in safe_walk(root):
        for name in files:
            path = os.path.join(current, name)
            try:
                if os.path.islink(path):
                    continue
                stat = os.stat(path, follow_symlinks=False)
                examined += 1
                if stat.st_size >= min_bytes:
                    found.append({
                        "path": path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
            except OSError:
                continue

    found.sort(key=lambda item: item["size"], reverse=True)
    frame("SEARCH RESULTS", [
        "Files examined : " + str(examined),
        "Large files    : " + str(len(found)),
        "Minimum size   : " + fmt_bytes(min_bytes),
        "Root           : " + root
    ], G)

    for item in found[:40]:
        stamp = datetime.fromtimestamp(item["modified"]).strftime("%Y-%m-%d")
        print("  " + Y + fmt_bytes(item["size"]).rjust(10) + R
              + " | " + stamp + " | " + item["path"])

    if len(found) > 40:
        print("  Showing first 40 files only.")

    print("\n  Nenhum arquivo foi modificado ou removido.")
    pause()


# -------------------- FILE ORGANIZER / PREVIEW --------------------

def file_category(filename):
    ext = os.path.splitext(filename)[1].lower()
    groups = {
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"},
        "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".3gp"},
        "Audio": {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"},
        "Documents": {".pdf", ".txt", ".doc", ".docx", ".odt", ".rtf", ".md"},
        "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
        "Installers": {".apk", ".xapk"},
        "Code": {".py", ".js", ".html", ".css", ".sh", ".java", ".json"}
    }
    for category, extensions in groups.items():
        if ext in extensions:
            return category
    return "Other"


def organizer():
    clear()
    header()
    frame("SMART FILE ORGANIZER", [
        "Mode: preview only",
        "No files are moved, renamed or deleted."
    ], P)

    root = ask_path("Pasta para analisar", "~")
    if not root or not os.path.isdir(root):
        print(RED + "  Pasta inválida ou inacessível." + R)
        pause()
        return

    print("\n  [1] Ordenar por tamanho")
    print("  [2] Ordenar por data de modificação")
    print("  [3] Agrupar por tipo")
    mode = input("  Escolha [1-3]: ").strip()
    if mode not in ("1", "2", "3"):
        print(Y + "  Opção inválida." + R)
        pause()
        return

    files = []
    for current, _dirs, names in safe_walk(root):
        for name in names:
            path = os.path.join(current, name)
            try:
                if os.path.islink(path):
                    continue
                st = os.stat(path, follow_symlinks=False)
                files.append({
                    "path": path,
                    "name": name,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "category": file_category(name)
                })
            except OSError:
                continue

    if mode == "1":
        files.sort(key=lambda x: x["size"], reverse=True)
    elif mode == "2":
        files.sort(key=lambda x: x["mtime"], reverse=True)
    else:
        files.sort(key=lambda x: (x["category"], x["name"].lower()))

    frame("ORGANIZATION PREVIEW", [
        "Directory : " + root,
        "Files     : " + str(len(files)),
        "Order     : " + {
            "1": "Largest first",
            "2": "Newest first",
            "3": "Grouped by category"
        }[mode]
    ], C)

    if mode == "3":
        counts = {}
        for item in files:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        for category in sorted(counts):
            print("  " + P + category.ljust(16) + R + str(counts[category]))

    for item in files[:60]:
        date = datetime.fromtimestamp(item["mtime"]).strftime("%Y-%m-%d %H:%M")
        print("  " + D + item["category"][:12].ljust(12) + R
              + " | " + fmt_bytes(item["size"]).rjust(9)
              + " | " + date + " | " + item["path"])

    if len(files) > 60:
        print("  " + D + "Mostrando 60 itens; nenhum arquivo foi alterado." + R)

    print("\n  Esta versão só apresenta uma prévia. Ela não move nem renomeia arquivos.")
    pause()


# -------------------- NETWORK SCANNER --------------------

def network_scanner():
    clear()
    header()

    rows = []
    try:
        for name in sorted(os.listdir("/sys/class/net")):
            state = read_text("/sys/class/net/" + name + "/operstate") or "unknown"
            mac = read_text("/sys/class/net/" + name + "/address") or "N/A"
            rows.append(name + " | " + state.upper() + " | MAC " + mac)
    except OSError:
        rows = ["Network interface information unavailable."]

    frame("NETWORK INTERFACES", rows, C)

    ip_cmd = shutil.which("ip")
    if ip_cmd:
        addresses = command([ip_cmd, "-brief", "address"])
        routes = command([ip_cmd, "route"])
    else:
        addresses = ""
        routes = ""

    frame("IP ADDRESSES", [
        addresses or "IP details unavailable; the ip command is not accessible."
    ], P)

    frame("ROUTES", [
        routes or "Route details unavailable on this device."
    ], Y)

    print("\n  Network interfaces do not guarantee internet connectivity.")
    pause()


# -------------------- REPORT VAULT --------------------

def collect_report():
    ram = ram_data()
    battery_data = {}
    if shutil.which("termux-battery-status"):
        raw = command(["termux-battery-status"])
        try:
            battery_data = json.loads(raw)
        except (ValueError, TypeError):
            battery_data = {"status": "Could not parse battery output"}

    return {
        "application": APP,
        "version": VERSION,
        "timestamp": datetime.now().astimezone().isoformat(),
        "device": device_info(),
        "uptime_seconds": uptime(),
        "load_average": load_average(),
        "memory": ram,
        "battery": battery_data,
        "storage": storage_info(),
        "network_interfaces": network_interfaces_for_report()
    }


def network_interfaces_for_report():
    items = []
    try:
        for name in sorted(os.listdir("/sys/class/net")):
            items.append({
                "name": name,
                "state": read_text("/sys/class/net/" + name + "/operstate") or "unknown",
                "mac": read_text("/sys/class/net/" + name + "/address") or "N/A"
            })
    except OSError:
        pass
    return items


def ensure_vault():
    os.makedirs(VAULT, exist_ok=True)


def report_files():
    ensure_vault()
    try:
        return sorted(
            [
                os.path.join(VAULT, name)
                for name in os.listdir(VAULT)
                if name.endswith(".json")
                and os.path.isfile(os.path.join(VAULT, name))
            ],
            key=os.path.getmtime,
            reverse=True
        )
    except OSError:
        return []


def save_report():
    ensure_vault()
    report = collect_report()
    filename = "diagnostic_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    path = os.path.join(VAULT, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return path


def report_vault():
    while True:
        clear()
        header()
        frame("REPORT VAULT", [
            "[1] Save new diagnostic",
            "[2] List saved reports",
            "[3] Compare two reports",
            "[0] Return"
        ], P)

        choice = input("\n  VAULT > ").strip()

        if choice == "0":
            return

        if choice == "1":
            try:
                path = save_report()
                frame("REPORT SAVED", [
                    G + "SUCCESS" + R,
                    os.path.basename(path),
                    path
                ], G)
            except Exception as exc:
                frame("SAVE ERROR", [str(exc)], RED)
            pause()

        elif choice == "2":
            files = report_files()
            rows = []
            for path in files[:50]:
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    rows.append(
                        os.path.basename(path) + " | " +
                        str(data.get("timestamp", "unknown"))
                    )
                except Exception:
                    rows.append(os.path.basename(path) + " | unreadable")

            frame("SAVED DIAGNOSTICS", rows or ["No reports saved yet."], C)
            pause()

        elif choice == "3":
            compare_reports()
        else:
            print(Y + "  Invalid choice." + R)
            time.sleep(0.8)


def compare_reports():
    files = report_files()
    if len(files) < 2:
        print(Y + "\n  São necessários pelo menos dois relatórios." + R)
        pause()
        return

    print("\n  Relatórios disponíveis:")
    for i, path in enumerate(files[:30], 1):
        print("  [{}] {}".format(i, os.path.basename(path)))

    try:
        a = int(input("\n  Número do relatório A: ").strip())
        b = int(input("  Número do relatório B: ").strip())
        if a == b or not (1 <= a <= min(30, len(files))) or not (1 <= b <= min(30, len(files))):
            raise ValueError
        with open(files[a-1], encoding="utf-8") as f:
            old = json.load(f)
        with open(files[b-1], encoding="utf-8") as f:
            new = json.load(f)
    except (ValueError, OSError, json.JSONDecodeError):
        print(RED + "  Seleção inválida ou relatório ilegível." + R)
        pause()
        return

    old_ram = old.get("memory", {})
    new_ram = new.get("memory", {})

    rows = [
        "A: " + os.path.basename(files[a-1]),
        "B: " + os.path.basename(files[b-1]),
        "RAM used A: " + fmt_bytes(old_ram.get("used_bytes", 0)),
        "RAM used B: " + fmt_bytes(new_ram.get("used_bytes", 0)),
        "RAM total A: " + fmt_bytes(old_ram.get("total_bytes", 0)),
        "RAM total B: " + fmt_bytes(new_ram.get("total_bytes", 0)),
        "Uptime A: " + fmt_time(old.get("uptime_seconds")),
        "Uptime B: " + fmt_time(new.get("uptime_seconds")),
        "Device A: " + str(old.get("device", {}).get("model", "N/A")),
        "Device B: " + str(new.get("device", {}).get("model", "N/A"))
    ]

    if old_ram.get("used_bytes") is not None and new_ram.get("used_bytes") is not None:
        delta = new_ram.get("used_bytes", 0) - old_ram.get("used_bytes", 0)
        rows.append("RAM usage change: " + ("+" if delta > 0 else "") + fmt_bytes(delta))

    frame("REPORT COMPARISON", rows, C)
    pause()


# -------------------- MAIN MENU --------------------

def menu():
    while True:
        clear()
        header()

        ram = ram_data()
        frame("LIVE SNAPSHOT", [
            "Device : " + (prop("ro.product.model") or platform.machine()),
            "Android: " + (prop("ro.build.version.release") or "N/A"),
            "RAM    : " + bar(ram["percent"]),
            "Uptime : " + fmt_time(uptime())
        ], G)

        frame("CONTROL CENTER", [
            G + "[1]" + R + "  Device information",
            G + "[2]" + R + "  Performance radar",
            G + "[3]" + R + "  Large file detector",
            G + "[4]" + R + "  Smart file organizer",
            G + "[5]" + R + "  Report vault & comparison",
            G + "[6]" + R + "  Local network scanner",
            RED + "[0]" + R + "  Exit"
        ], C)

        choice = input("\n  " + G + "M4RT1NS" + R + " @android > ").strip()

        actions = {
            "1": device_center,
            "2": performance_radar,
            "3": large_file_finder,
            "4": organizer,
            "5": report_vault,
            "6": network_scanner
        }

        if choice == "0":
            clear()
            header()
            frame("SESSION CLOSED", [
                "M4RT1NS.exe encerrado.",
                "Seus relatórios permanecem na pasta reports."
            ], G)
            break

        action = actions.get(choice)
        if action:
            try:
                action()
            except KeyboardInterrupt:
                pass
            except Exception as exc:
                print(RED + "\n  Erro: " + str(exc) + R)
                pause()
        else:
            print(Y + "  Opção inválida." + R)
            time.sleep(0.8)


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n" + G + "M4RT1NS.exe encerrado." + R)
