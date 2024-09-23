#!/bin/bash

# Benutzername und Passwort
USER="user"
PASSWORD="SoSe2024"

# Quellpfad der Dateien
SOURCE_PATH="/home/skon/Desktop/Unikram/praktikum/networking/"

# Dateien, die kopiert werden sollen
FILES=("messages.py" "clientServerExample.py")

# Präfix der IP-Adressen
IP_PREFIX="192.168.8."

# Liste der letzten drei Ziffern der IP-Adressen
IP_SUFFIXES=(110 224 147 230)

# Funktion zum Kopieren von Dateien mithilfe von `scp`
copy_files(){
    local IP_SUFFIX=$1
    IP="${IP_PREFIX}${IP_SUFFIX}"

    for FILE in "${FILES[@]}"; do
        echo "Kopiere Datei $FILE zu $USER@$IP:~/"
        # Verwendung von scp zum Kopieren der Datei
        sshpass -p "$PASSWORD" scp "$SOURCE_PATH$FILE" "$USER@$IP:~/"
        if [ $? -eq 0 ]; then
            echo "Datei $FILE erfolgreich kopiert nach $USER@$IP:~/"
        else
            echo "Fehler beim Kopieren von $FILE nach $USER@$IP:~/"
        fi
    done
}

# Iteriere über die IP-Suffixes und kopiere die Dateien
for SUFFIX in "${IP_SUFFIXES[@]}"; do
    copy_files $SUFFIX
done

