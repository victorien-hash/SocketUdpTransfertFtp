import socket
import random
import os
import hashlib


Adresse_serveur = "127.0.0.1"  # Adresse_serveur IP du serveur
Port_serveur = 2212  # Port_serveur d'écoute
Taille_bloc = 1024  # Taille des blocs de données
Taille_fenetre = 5 # nombre de blocs envoyés avant une confirmation
Timeout = 3  # en secondes
Max_tentatives = 5 # nombre de tentatives de retransmission
Fiabilite = 0.95  # valeur de la fiabilité du réseau
Emplacement_fichiers = "fichiers_serveur" # Dossier contenant les fichiers du serveur que le client va pouvoir telecharger

# Création du socket UDP pour le serveur
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((Adresse_serveur, Port_serveur))


def simulation_packet_perdu():
    """Simule une perte de paquets en fonction de la fiabilité du réseau."""
    return random.random() > Fiabilite

def envoi_avec_simulation_de_perte(data, address):
    """Envoie des données avec simulation de perte d'information."""
    if not simulation_packet_perdu():      # si le paquet n'est pas perdu 
        server_socket.sendto(data, address)  #  Envoi des données


def reception_ack():
    """Réception d'un accusé de réception."""
    try:
        ack, _ = server_socket.recvfrom(Taille_bloc)
        ack_msg = ack.decode()
        return ack_msg
    except socket.timeout:
        print(f"Aucun ack recu du client.")
        return None
    


def envoyer_fichier(filename, client_address):
    """Envoie un fichier au client en découpant le fichier en blocs numérotés."""
    global Taille_bloc, Emplacement_fichiers, Taille_fenetre, Max_tentatives, Timeout # Accès aux variables globales qui sont en haut

    file_path = os.path.join(Emplacement_fichiers, filename) # Chemin complet du fichier
    if not os.path.exists(file_path):
        envoi_avec_simulation_de_perte("ERROR: Fichier introuvable".encode(), client_address)
        
    taille_fichier = os.path.getsize(file_path)  # Taille totale du fichier


    print(f"Envoi du fichier '{filename}' de taille ({taille_fichier/1000} Ko) au client...")

    # Calculer le checksum du fichier
    hasher = hashlib.sha256() 
    with open(file_path, "rb") as f: # Ouvrir le fichier en mode binaire
        while morceau := f.read(Taille_bloc): # Lire le fichier en blocs de Taille_bloc octets
            hasher.update(morceau)  # Mettre à jour le checksum
    checksum_fichier_original = hasher.hexdigest() 
    print(f"Checksum du fichier (SHA-256) : {checksum_fichier_original}")

    # Envoyer le checksum au client
    server_socket.sendto(f"CHECKSUM:{checksum_fichier_original}".encode(), client_address)
    print(f"Checksum envoyé : {checksum_fichier_original}")




    with open(file_path, "rb") as f:
        numero_de_sequence = 0  # Numéro de séquence initial
        compteur_de_tentative = 0  # Compteur de tentatives d'envoi
        debut_fenetre = 0  # Début de la fenêtre courante


        while True:
            f.seek(numero_de_sequence * Taille_bloc)  # Se placer au bon endroit dans le fichier
            morceau = f.read(Taille_bloc)  # Lire le bloc de taille Taille_bloc
            if not morceau:  # Fin du fichier
                break

            # Ajout du numéro de séquence au début du bloc pour le numeroter et l'envoyer au client
            packet = numero_de_sequence.to_bytes(4, byteorder='big') + morceau #transformer le numero de sequence en bytes et l'ajouter au debut du morceau
            server_socket.sendto(packet, client_address)
            print(f"Envoi du bloc {numero_de_sequence}")

            # Vérifier si un ACK doit être reçu (tous les `Taille_fenetre` blocs)
            if (numero_de_sequence + 1) % Taille_fenetre == 0:
                ack_received = False
                while not ack_received and compteur_de_tentative < Max_tentatives:
                    try:
                        server_socket.settimeout(Timeout)  # Attendre un ACK pendant 3 secondes
                        ack_data, _ = server_socket.recvfrom(1024)  # Réception d'un ACK
                        ack_message = ack_data.decode()
                        print(f"Accusé reçu : {ack_message}")
                        ack_received = True
                        compteur_de_tentative = 0  # Réinitialiser le compteur de tentatives
                        debut_fenetre = numero_de_sequence + 1  # Déplacer le début de la fenêtre
                    except socket.timeout:
                        compteur_de_tentative += 1
                        print(f"Aucun accusé reçu. Tentative {compteur_de_tentative}/{Max_tentatives}...")
                        # Réexpédier les blocs de la fenêtre courante
                        for i in range(debut_fenetre, numero_de_sequence + 1): 
                            f.seek(i * Taille_bloc) # On se place dans le fichier à l’endroit où commence le bloc numéro i
                            morceau = f.read(Taille_bloc)

                            # On prépare le paquet à envoyer 
                            # On encode le numéro de séquence sur 4 octets (big-endian)
                            # On y ajoute le morceau de données
                            packet = i.to_bytes(4, byteorder='big') + morceau
                            envoi_avec_simulation_de_perte(packet, client_address)
                            # On affiche un message pour dire qu’on a réenvoyé ce bloc
                            print(f"Réexpédition du bloc {i}")
                    except socket.error as e:
                        print(f"Erreur de socket : {e}")
                        break
                    finally:
                        server_socket.settimeout(None)  # Remettre le socket en mode normal pour continuer le traitement

                # Si le nombre maximum de tentatives est atteint on envoie un message d'erreur au client
                if compteur_de_tentative >= Max_tentatives:
                    print("Échec du transfert après 5 tentatives")
                    envoi_avec_simulation_de_perte("ERROR: Échec du transfert".encode(), client_address)
                    return

            numero_de_sequence += 1  # On incremente le numéro de séquence

 
    # Envoyer un message de fin de transmission
    envoi_avec_simulation_de_perte(numero_de_sequence.to_bytes(4, byteorder='big') + b"END", client_address)
    print("Envoi du fichier terminé !")

    

# Au demarrage du fichier, on affiche l'adresse et le port sur lequel le serveur est en ecoute
print(f"Serveur en écoute sur {Adresse_serveur}:{Port_serveur}")


while True:
    
    data, client_address = server_socket.recvfrom(Taille_bloc)
    message = data.decode()

    # processus du three way handshake pour la connexion d'un client
    if message.startswith("SYN"):
        # Réception du SYN du client et envoi du SYN-ACK
        print(f"SYN reçu du client {client_address}. \nEnvoi du SYN-ACK...")
        envoi_avec_simulation_de_perte("SYN-ACK".encode(), client_address)
        
        # Attente du ACK du client
        response = reception_ack()
        if response and response.startswith("ACK"):
            print(f"ACK reçu du client {client_address}. \nConnexion établie.")
            
            # Le client a accepté la connexion,on envoie donc les paramètres de connexion au client
            params = f"ACK {Taille_bloc} {Taille_fenetre}"
            envoi_avec_simulation_de_perte(params.encode(), client_address)
        else:
            print("Erreur lors de l'établissement de la connexion avec le client.")


    # gestion des commandes recues du client
    elif message.startswith("ls"):
        # Lister les fichiers dans le répertoire de téléchargement
        files = os.listdir(Emplacement_fichiers)
        envoi_avec_simulation_de_perte(", ".join(files).encode(), client_address)
    
    elif message.startswith("get"):
        filename = message.split()[1]
        envoyer_fichier(filename, client_address)
    
    elif message.startswith("bye"):
        print(f"Déconnexion de {client_address}")


