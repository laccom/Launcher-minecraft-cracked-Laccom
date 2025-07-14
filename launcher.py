import os
import subprocess
import requests
import shutil
import json
import zipfile
import minecraft_launcher_lib

# === CONFIGURATION === #
FORGE_VERSION = "1.20.4-49.2.0"
MC_VERSION = "1.20.4"
RAM = "2G"
MODS_ZIP_URL = "https://lac.laccom.org/mods.zip"

# === CHEMINS === #
base_dir = os.path.dirname(__file__)
minecraft_dir = os.path.join(base_dir, "minecraft_forge")
versions_dir = os.path.join(minecraft_dir, "versions")
config_path = os.path.join(base_dir, "config.json")

# Forge version folder corrigé
forge_version_id = f"{MC_VERSION}-forge-{FORGE_VERSION.split('-')[1]}"

installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{FORGE_VERSION}/forge-{FORGE_VERSION}-installer.jar"
installer_path = os.path.join(base_dir, f"forge-installer-{FORGE_VERSION}.jar")
mods_dir = os.path.join(minecraft_dir, "mods")
mods_zip_path = os.path.join(base_dir, "mods.zip")

# === FONCTIONS === #

def get_username():
    # Cherche config.json
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "username" in data and data["username"].strip():
                print(f"Pseudo chargé depuis config.json : {data['username']}")
                return data["username"]
        except Exception:
            pass
    
    # Sinon demande à l'utilisateur
    username = ""
    while not username.strip():
        username = input("Entrez votre pseudo Minecraft (offline mode) : ").strip()

    # Sauvegarde dans config.json
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"username": username}, f, indent=4)
    print(f"Pseudo '{username}' sauvegardé dans config.json")
    return username

def ensure_dirs():
    os.makedirs(minecraft_dir, exist_ok=True)
    os.makedirs(versions_dir, exist_ok=True)
    os.makedirs(mods_dir, exist_ok=True)

def download_forge_installer():
    if os.path.exists(installer_path):
        print("Installeur Forge déjà téléchargé.")
        return
    print("Téléchargement de l'installeur Forge...")
    r = requests.get(installer_url)
    r.raise_for_status()
    with open(installer_path, "wb") as f:
        f.write(r.content)
    print("Forge téléchargé.")

def install_minecraft_base():
    print(f"Installation de Minecraft {MC_VERSION}...")
    minecraft_launcher_lib.install.install_minecraft_version(MC_VERSION, minecraft_dir)
    print("Minecraft installé.")

def create_fake_launcher_profile(temp_minecraft_dir):
    profile_path = os.path.join(temp_minecraft_dir, "launcher_profiles.json")
    profile_data = {
        "profiles": {
            "default": {
                "name": "default",
                "lastVersionId": MC_VERSION
            }
        },
        "selectedProfile": "default"
    }
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=4)
    print("Fichier launcher_profiles.json créé dans le dossier temporaire.")

def install_forge():
    if os.path.exists(os.path.join(versions_dir, forge_version_id)):
        print(f"Forge {forge_version_id} déjà installé, installation ignorée.")
        return

    print("Installation de Forge (silencieuse)...")

    temp_minecraft_dir = os.path.join(base_dir, "temp_minecraft")
    os.makedirs(temp_minecraft_dir, exist_ok=True)

    create_fake_launcher_profile(temp_minecraft_dir)

    subprocess.run([
        "java", "-jar", installer_path, "--installClient"
    ], cwd=temp_minecraft_dir, check=True)

    temp_forge_dir = os.path.join(temp_minecraft_dir, "versions", forge_version_id)
    dest_forge_dir = os.path.join(minecraft_dir, "versions", forge_version_id)
    os.makedirs(os.path.dirname(dest_forge_dir), exist_ok=True)

    if os.path.exists(dest_forge_dir):
        shutil.rmtree(dest_forge_dir)
    shutil.copytree(temp_forge_dir, dest_forge_dir)

    temp_lib_dir = os.path.join(temp_minecraft_dir, "libraries")
    dest_lib_dir = os.path.join(minecraft_dir, "libraries")
    if os.path.exists(temp_lib_dir):
        shutil.copytree(temp_lib_dir, dest_lib_dir, dirs_exist_ok=True)

    shutil.rmtree(temp_minecraft_dir)
    print("Forge installé dans le dossier local.")

def download_and_install_mods():
    print("Téléchargement des mods...")
    r = requests.get(MODS_ZIP_URL, stream=True)
    r.raise_for_status()
    with open(mods_zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Mods téléchargés.")

    print("Installation des mods...")
    with zipfile.ZipFile(mods_zip_path, 'r') as zip_ref:
        zip_ref.extractall(mods_dir)
    print(f"Mods extraits dans {mods_dir}")

    os.remove(mods_zip_path)

def launch_game(username):
    options = {
        "username": username,
        "uuid": "00000000-0000-0000-0000-000000000000",
        "token": "0",
        "jvmArguments": [f"-Xmx{RAM}"]
    }

    print("Préparation au lancement...")
    command = minecraft_launcher_lib.command.get_minecraft_command(forge_version_id, minecraft_dir, options)

    print("Lancement de Minecraft Forge...")
    subprocess.run(command)

# === MAIN === #

def main():
    print("=== Launcher Minecraft Forge 1.20.4 (Automatisé sans GUI) ===")
    username = get_username()
    ensure_dirs()
    install_minecraft_base()
    download_forge_installer()
    install_forge()
    download_and_install_mods()
    launch_game(username)


if __name__ == "__main__":
    main()
