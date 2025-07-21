import os
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
import logging
import threading
import time

# Логирование ошибок
logging.basicConfig(
    filename="error_log.txt",
    level=logging.ERROR,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

# Настройки
DEFAULT_DIRS = [
    os.environ.get("TEMP", ""),
    os.path.join(os.environ.get("WINDIR", ""), "Temp"),
    os.path.join(os.environ.get("WINDIR", ""),
                 "SoftwareDistribution", "Download"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    os.path.join(os.environ.get("WINDIR", ""), "Logs"),
    os.path.join(os.environ.get("APPDATA", ""),
                 "Microsoft", "Windows", "Recent"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 "Microsoft", "Windows", "Explorer"),
]

# Ключевые слова для исключения важных файлов
EXCLUDE_KEYWORDS = {
    "login data", "cookies", "web data", "bookmarks", "history", "preferences",
    "current sessions", "extension", "extensions", "local storage", "databases",
    "sessions", "key", "secret", "password", "autofill", "topsites", "favicons",
    "recovery", "wallet", "auth", "account", "token", "cache index",
}

# Папки, которые могут быть кэшем
CACHE_FOLDERS_TO_SCAN = {
    "Cache", "cache", "cache2", "User Data", "Profile", "Default", "entries",
    "Opera Stable", "Brave-Browser", "YandexBrowser", ".mozilla",
    "temp", "tmp", "download", "updates", "logs", "recent", "thumbnails"
}

# Пути, которые НИКОГДА не удаляем
BLACKLIST_PATHS = {
    os.environ.get("APPDATA", ""),
    os.environ.get("LOCALAPPDATA", ""),
    os.environ.get("PROGRAMFILES", ""),
    os.environ.get("PROGRAMFILES(X86)", ""),
    os.environ.get("PROGRAMDATA", ""),
    os.path.join(os.environ.get("WINDIR", ""), "System32"),
    os.path.join(os.environ.get("WINDIR", ""), "SysWOW64")
}

# Глобальные переменные
found_files = []
categorized_files = {}
category_vars = {}

# Форматирование размера файла


def format_size(size_bytes):
    return round(size_bytes / (1024 * 1024), 2)

# Проверка: можно ли удалять файл?


def should_delete(path):
    if not os.path.exists(path):
        return False
    name = os.path.basename(path).lower()
    if any(kw in name for kw in EXCLUDE_KEYWORDS):
        return False
    if any(path.startswith(bl_path) for bl_path in BLACKLIST_PATHS if bl_path):
        return False
    return True

# Поиск кэша браузеров


def find_browser_cache(base_path, cache_folder="Cache"):
    if not os.path.exists(base_path):
        return []
    found = []
    for profile in os.listdir(base_path):
        full_profile_path = os.path.join(base_path, profile)
        if not os.path.isdir(full_profile_path):
            continue
        cache_path = os.path.join(full_profile_path, cache_folder)
        if os.path.exists(cache_path):
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if should_delete(full_path):
                        found.append(
                            (full_path, format_size(os.path.getsize(full_path))))
    return found

# Сканирование дисков на наличие кэша


def scan_all_drives_for_cache():
    drives = [
        f"{d}:\\\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    found = []
    for drive in drives:
        for root, dirs, files in os.walk(drive, topdown=True, onerror=lambda _: None, followlinks=False):
            if root.count(os.sep) - drive.count(os.sep) > 5:
                dirs[:] = []
                continue
            for folder in CACHE_FOLDERS_TO_SCAN:
                if folder in dirs:
                    cache_path = os.path.join(root, folder)
                    try:
                        if not os.path.exists(cache_path):
                            continue
                        for r, d, f in os.walk(cache_path):
                            for file in f:
                                full_path = os.path.join(r, file)
                                if should_delete(full_path):
                                    found.append(
                                        (full_path, format_size(os.path.getsize(full_path))))
                        dirs.remove(folder)
                    except Exception as e:
                        logging.error(
                            f"Ошибка при сканировании: {cache_path} — {e}")
    return found

# Кэш Firefox


def find_firefox_cache(path):
    if not os.path.exists(path):
        return []
    found = []
    for profile in os.listdir(path):
        full_profile_path = os.path.join(path, profile)
        if not os.path.isdir(full_profile_path):
            continue
        cache_path = os.path.join(full_profile_path, "cache2", "entries")
        if os.path.exists(cache_path):
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if should_delete(full_path):
                        found.append(
                            (full_path, format_size(os.path.getsize(full_path))))
    return found


# Категории
CATEGORIES = {
    "System Temp": [],
    "Browser Cache": [],
    "Windows Cache": [],
    "Recent/Prefetch": [],
    "Other Temp": [],
}

# Распределение файлов по категориям


def categorize_files(files):
    categorized = {k: [] for k in CATEGORIES}
    for path, size in files:
        path = path.lower()
        if "temp" in path or "tmp" in path:
            categorized["System Temp"].append((path, size))
        elif "cache" in path or "browser" in path or "chrome" in path or "brave" in path or "opera" in path:
            categorized["Browser Cache"].append((path, size))
        elif "logs" in path or "softwaredistribution" in path:
            categorized["Windows Cache"].append((path, size))
        elif "recent" in path or "prefetch" in path:
            categorized["Recent/Prefetch"].append((path, size))
        else:
            categorized["Other Temp"].append((path, size))
    return categorized

# Начать сканирование


def find_files():
    status_label.config(text="🔍 Scanning files... Estimated time: ~30s left")
    threading.Thread(target=scan_files_thread, daemon=True).start()

# Поток сканирования


def scan_files_thread():
    global found_files, categorized_files
    found_files = []
    start_time = time.time()
    all_dirs = [d for d in DEFAULT_DIRS if os.path.exists(d)]
    total_steps = len(all_dirs) + 4
    step = 0
    time_per_step = []

    # Сканирование системных папок
    for directory in all_dirs:
        for root, dirs, files in os.walk(directory):
            for file in files:
                full_path = os.path.join(root, file)
                if should_delete(full_path):
                    try:
                        found_files.append(
                            (full_path, format_size(os.path.getsize(full_path))))
                    except Exception as e:
                        logging.error(f"Error: cannot add {full_path} — {e}")
        step += 1
        elapsed = time.time() - start_time
        time_per_step.append(elapsed / step)
        avg_time = sum(time_per_step) / len(time_per_step)
        remaining = int(avg_time * (total_steps - step))
        app.after(0, lambda r=remaining: status_label.config(
            text=f"🔍 Scanning files... Estimated time: ~{r}s left"
        ))
        time.sleep(0.1)

    # Сканирование браузеров
    chrome_path = os.path.join(
        os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data")
    found_files.extend(find_browser_cache(chrome_path))

    brave_path = os.path.join(
        os.environ["LOCALAPPDATA"], "BraveSoftware", "Brave-Browser", "User Data")
    found_files.extend(find_browser_cache(brave_path))

    opera_path = os.path.join(
        os.environ["APPDATA"], "Opera Software", "Opera Stable")
    found_files.extend(find_browser_cache(opera_path))

    firefox_cache_path = os.path.join(
        os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles")
    found_files.extend(find_firefox_cache(firefox_cache_path))

    found_files.extend(scan_all_drives_for_cache())

    # Категоризация
    categorized_files = categorize_files(found_files)
    total_time = int(time.time() - start_time)
    total_size = sum(size for _, size in found_files)
    app.after(0, lambda: status_label.config(
        text=f"✅ Found {len(found_files)} files. Total size: {total_size:.2f} MB | Took {total_time}s"
    ))
    app.after(0, lambda: update_category_view())

# Обновление отображения категорий


def update_category_view():
    for widget in file_frame.winfo_children():
        widget.destroy()
    for category in categorized_files:
        var = tk.BooleanVar(value=True)
        category_vars[category] = var
        frame = tk.Frame(file_frame, bg="#1e1e1e")
        frame.pack(fill='x', padx=5, pady=2)
        cb = tk.Checkbutton(
            frame, text=f"📁 {category} — {sum(size for _, size in categorized_files[category]):.2f} MB",
            variable=var, bg="#1e1e1e", fg="white", selectcolor="#333333", anchor='w'
        )
        cb.pack(fill='x')

# Удаление выбранных категорий


def delete_files_by_category():
    deleted_count = 0
    freed_space = 0
    status_label.config(text="🗑️ Deleting files...")
    app.update_idletasks()
    for category, data in category_vars.items():
        if data.get():
            for path, size in categorized_files[category]:
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        deleted_count += 1
                        freed_space += size
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                        deleted_count += 1
                        freed_space += size
                except Exception as e:
                    logging.error(f"Ошибка при удалении: {path} — {e}")
                    messagebox.showerror("Error", f"Could not delete: {path}")
    messagebox.showinfo(
        "Result", f"Deleted {deleted_count} files. Freed: {freed_space:.2f} MB")
    find_files()

# Удалить все


def delete_all_categories():
    for category in category_vars:
        category_vars[category].set(True)
    delete_files_by_category()

# Удалить выбранное


def delete_selected_categories():
    confirm = messagebox.askyesno("Confirm", "Delete selected categories?")
    if confirm:
        delete_files_by_category()


# GUI
app = tk.Tk()
app.title("TrashCleaner")
app.geometry("1100x850")
app.resizable(False, False)
app.configure(bg="#1e1e1e")

# Кнопки
btn_frame = tk.Frame(app, bg="#1e1e1e")
btn_frame.pack(pady=10)
find_btn = tk.Button(btn_frame, text="Find Temporary Files",
                     width=25, command=find_files, bg="#444444", fg="white")
find_btn.pack(side=tk.LEFT, padx=5)
delete_all_btn = tk.Button(btn_frame, text="Delete All Categories",
                           width=25, command=delete_all_categories, bg="#444444", fg="white")
delete_all_btn.pack(side=tk.LEFT, padx=5)
delete_selected_btn = tk.Button(btn_frame, text="Delete Selected Categories",
                                width=25, command=delete_selected_categories, bg="#444444", fg="white")
delete_selected_btn.pack(side=tk.LEFT, padx=5)

# Список категорий
canvas = tk.Canvas(app, bg="#1e1e1e", highlightthickness=0)
scrollbar = tk.Scrollbar(app, orient="vertical", command=canvas.yview)
file_frame = tk.Frame(canvas, bg="#1e1e1e")
file_frame.bind("<Configure>", lambda e: canvas.configure(
    scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=file_frame,
                     anchor="nw", width=canvas.winfo_reqwidth())
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scrollbar.pack(side="right", fill="y")

# Статусбар
status_label = tk.Label(app, text="Ready — Click 'Find Temporary Files'",
                        bd=1, relief=tk.SUNKEN, bg="#2a2a2a", fg="white")
status_label.pack(side=tk.BOTTOM, fill=tk.X)

# Меню


def show_about():
    messagebox.showinfo(
        "About", "🧹 TrashCleaner\nVersion: 1.0\nAuthor: Sad Scob\nGitHub: https://github.com/iamscob ")


menubar = tk.Menu(app)
helpmenu = tk.Menu(menubar, tearoff=0)
helpmenu.add_command(label="About", command=show_about)
menubar.add_cascade(label="Help", menu=helpmenu)
app.config(menu=menubar)

# Инициализация
category_vars = {}
app.mainloop()
