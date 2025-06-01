import os
import subprocess
import urllib.request
import json
import zipfile
import threading
import tempfile
import sys
import io
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

VERSION = "1.20.4"
MC_DIR = os.path.join(os.getcwd(), "minecraft")
JDK_BASE_DIR = "C:\\jdk-21"
JDK_DOWNLOAD_URL = "https://download.oracle.com/java/21/latest/jdk-21_windows-x64_bin.zip"

root = tk.Tk()
root.title("Laccom Minecraft")
root.geometry("450x280")
root.resizable(False, False)

def load_background_image(url):
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
        image = Image.open(io.BytesIO(data))
        image = image.resize((450, 280), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        print("Erreur chargement image de fond:", e)
        return None

background_image = load_background_image("https://cdn.laccom.org/minecraft.png")
if background_image:
    bg_label = tk.Label(root, image=background_image)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

style = ttk.Style(root)
style.theme_use('clam')
style.configure("TFrame", background="#2d2d2d")
style.configure("TLabel", background="#2d2d2d", foreground="white", font=("Segoe UI", 11))
style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1abc9c")
style.configure("TEntry", font=("Segoe UI", 12))
style.configure("TButton", font=("Segoe UI", 13, "bold"), background="#1abc9c", foreground="white")

frame = ttk.Frame(root, padding=30, style="TFrame")
frame.place(relx=0.5, rely=0.5, anchor="center")

label_title = ttk.Label(frame, text="Laccom Minecraft", style="Title.TLabel")
label_username = ttk.Label(frame, text="Pseudo :", style="TLabel")
entry_username = ttk.Entry(frame)
entry_username.insert(0, "Player")

label_status = ttk.Label(frame, text="", style="TLabel")
label_resources = ttk.Label(frame, text="", style="TLabel")

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100, length=300)

btn_install = ttk.Button(frame, text="Installer Minecraft")
btn_launch = ttk.Button(frame, text="Lancer Minecraft")

resources_downloaded = 0
resources_total = 0

def find_java_executable(base_dir=JDK_BASE_DIR):
    if not os.path.exists(base_dir):
        return None
    for entry in os.listdir(base_dir):
        full_path = os.path.join(base_dir, entry)
        if os.path.isdir(full_path) and entry.startswith("jdk-21"):
            java_path = os.path.join(full_path, "bin", "java.exe")
            if os.path.exists(java_path):
                return java_path
    return None

def check_java_version():
    java_path = find_java_executable()
    if not java_path:
        return False
    try:
        result = subprocess.run([java_path, "-version"], capture_output=True, text=True)
        output = result.stderr + result.stdout
        return "version \"21" in output
    except Exception:
        return False

def download_and_install_jdk():
    label_status.config(text="Téléchargement de JDK 21 en cours...")
    root.update_idletasks()

    try:
        temp_dir = tempfile.mkdtemp()
        jdk_zip_path = os.path.join(temp_dir, "jdk21.zip")

        with urllib.request.urlopen(JDK_DOWNLOAD_URL) as response, open(jdk_zip_path, 'wb') as out_file:
            out_file.write(response.read())

        label_status.config(text="Extraction de JDK 21...")
        root.update_idletasks()

        if not os.path.exists(JDK_BASE_DIR):
            os.makedirs(JDK_BASE_DIR, exist_ok=True)

        with zipfile.ZipFile(jdk_zip_path, 'r') as zip_ref:
            zip_ref.extractall(JDK_BASE_DIR)

        messagebox.showinfo("Installation terminée", "JDK 21 a été installé.\nRelancez le launcher.")
        root.destroy()
        sys.exit()
    except Exception as e:
        messagebox.showerror("Erreur installation JDK", str(e))
        label_status.config(text="")

def update_progress():
    if resources_total:
        percent = (resources_downloaded / resources_total) * 100
        progress_var.set(percent)
        label_resources.config(text=f"{int(percent)}% ({resources_downloaded}/{resources_total})")
        root.update_idletasks()

def download_file(url, dest):
    global resources_downloaded
    try:
        with urllib.request.urlopen(url) as response:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        resources_downloaded += 1
        update_progress()
    except Exception as e:
        messagebox.showerror("Erreur téléchargement", f"Erreur lors du téléchargement de:\n{url}\n\n{e}")
        raise

def do_download():
    global resources_downloaded, resources_total
    try:
        resources_downloaded = 0

        version_manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
        version_manifest = json.load(urllib.request.urlopen(version_manifest_url))

        version_data = next((v for v in version_manifest["versions"] if v["id"] == VERSION), None)
        version_json = json.load(urllib.request.urlopen(version_data["url"]))

        asset_index_path = os.path.join(MC_DIR, "assets", "indexes", f"{VERSION}.json")
        if not os.path.exists(asset_index_path):
            download_file(version_json["assetIndex"]["url"], asset_index_path)

        with open(asset_index_path) as f:
            assets_index_json = json.load(f)

        resources_total = len(assets_index_json["objects"]) + 2 + len(version_json["libraries"])

        version_jar_path = os.path.join(MC_DIR, f"{VERSION}.jar")
        if not os.path.exists(version_jar_path):
            download_file(version_json["downloads"]["client"]["url"], version_jar_path)

        for lib in version_json["libraries"]:
            if "downloads" in lib and "artifact" in lib["downloads"]:
                artifact = lib["downloads"]["artifact"]
                path = os.path.join(MC_DIR, "libraries", *artifact["path"].split("/"))
                if not os.path.exists(path):
                    download_file(artifact["url"], path)

            if "classifiers" in lib.get("downloads", {}):
                natives = lib["downloads"]["classifiers"].get("natives-windows", None)
                if natives:
                    path = os.path.join(MC_DIR, "libraries", *natives["path"].split("/"))
                    if not os.path.exists(path):
                        download_file(natives["url"], path)
                    extract_path = os.path.join(MC_DIR, "natives")
                    if not os.path.exists(extract_path):
                        with zipfile.ZipFile(path, 'r') as zip_ref:
                            os.makedirs(extract_path, exist_ok=True)
                            zip_ref.extractall(extract_path)

        for name, obj in assets_index_json["objects"].items():
            hash_ = obj["hash"]
            subdir = hash_[:2]
            url = f"https://resources.download.minecraft.net/{subdir}/{hash_}"
            path = os.path.join(MC_DIR, "assets", "objects", subdir, hash_)
            if not os.path.exists(path):
                download_file(url, path)

        messagebox.showinfo("Succès", "Minecraft téléchargé avec succès !")
        root.after(0, switch_to_launch_mode)

    except Exception as e:
        messagebox.showerror("Erreur", str(e))
    finally:
        btn_install.config(state="normal")
        label_status.config(text="")
        label_resources.config(text="")
        progress_var.set(0)

def download_minecraft_version():
    btn_install.config(state="disabled")
    label_status.pack(pady=(10, 0))
    progress_bar.pack(pady=5)
    label_resources.pack()
    threading.Thread(target=do_download, daemon=True).start()

def launch_minecraft_offline():
    username = entry_username.get().strip()
    if not username:
        messagebox.showwarning("Pseudo requis", "Merci d'entrer un pseudo.")
        return

    java_path = find_java_executable()
    if not java_path:
        messagebox.showerror("Java manquant", "Java n'est pas installé.")
        return

    version_jar = os.path.join(MC_DIR, f"{VERSION}.jar")
    natives_dir = os.path.join(MC_DIR, "natives")
    classpath = [version_jar]
    for root_dir, _, files in os.walk(os.path.join(MC_DIR, "libraries")):
        for file in files:
            if file.endswith(".jar"):
                classpath.append(os.path.join(root_dir, file))

    args = [
        java_path,
        f"-Djava.library.path={natives_dir}",
        "-cp", os.pathsep.join(classpath),
        "net.minecraft.client.main.Main",
        "--username", username,
        "--version", VERSION,
        "--gameDir", MC_DIR,
        "--assetsDir", os.path.join(MC_DIR, "assets"),
        "--assetIndex", VERSION,
        "--uuid", "00000000-0000-0000-0000-000000000000",
        "--accessToken", "0"
    ]
    try:
        subprocess.Popen(args)
    except Exception as e:
        messagebox.showerror("Erreur", str(e))

def switch_to_launch_mode():
    for widget in frame.winfo_children():
        widget.pack_forget()
    label_title.pack(pady=(0, 20))
    label_username.pack(anchor="w")
    entry_username.pack(fill="x", pady=5)
    btn_launch.pack(pady=20, fill="x")

def switch_to_install_mode():
    for widget in frame.winfo_children():
        widget.pack_forget()
    label_title.pack(pady=(0, 20))
    btn_install.pack(pady=40, fill="x")

btn_install.config(command=download_minecraft_version)
btn_launch.config(command=launch_minecraft_offline)

def main():
    if not check_java_version():
        if messagebox.askyesno("Java 21 requis", "Java 21 est nécessaire. Voulez-vous l'installer automatiquement ?"):
            download_and_install_jdk()
        else:
            root.destroy()
            sys.exit()

    if os.path.exists(os.path.join(MC_DIR, f"{VERSION}.jar")):
        switch_to_launch_mode()
    else:
        switch_to_install_mode()

    root.mainloop()

if __name__ == "__main__":
    main()
