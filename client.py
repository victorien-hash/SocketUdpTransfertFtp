import socket
import random
import hashlib


# Configuration du client
Adress_serveur = "127.0.0.1"  # Adresse IP du serveur
Port_serveur = 2212         # Port du serveur
Taille_bloc = 1024         # Taille du buffer
Taille_fenetre = 5 # nombre de blocs envoyés avant une confirmation
Timeout = 3  # en secondes
Fiabilite = 0.95  # valeur de la fiabilité du réseau


def simulation_packet_perdu():
    """Simule une perte de paquets en fonction de la fiabilité du réseau."""
    return random.random() > Fiabilite

def envoi_avec_simulation_de_perte(data, address):
    """Envoie des données avec simulation de perte d'information."""
    if not simulation_packet_perdu():       # si le paquet n'est pas perdu
        client_socket.sendto(data, address) #  Envoi des données


def reception_ack():
    """Réception d'un accusé de réception avec gestion de timeout."""
    try:
        ack, _ = client_socket.recvfrom(Taille_bloc)
        ack_msg = ack.decode()
        return ack_msg
    except socket.timeout:
        print(f"le serveur n'a pas repondu, veuillez reessayer en saisissant open <{Adress_serveur}>")
        return None


def connexion_au_serveur(ip):
    """Établit la connexion avec le serveur en réalisant le handshake."""
    global Adress_serveur, client_socket, Taille_bloc, Taille_fenetre, Timeout

    # Création du socket UDP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(Timeout)
    Adress_serveur = (ip, Port_serveur)

    # Envoi du SYN au serveur
    print("Envoi du SYN au serveur...")
    envoi_avec_simulation_de_perte("SYN".encode(), Adress_serveur)
    
    # Attente du SYN-ACK du serveur
    response = reception_ack()
    if response and response.startswith("SYN-ACK"):
        print("SYN-ACK reçu du serveur.")
        
        # Envoi du ACK au serveur
        print("Envoi du ACK au serveur...")
        envoi_avec_simulation_de_perte("ACK".encode(), Adress_serveur)
        
        # Réception des paramètres de connexion venant du serveur
        response = reception_ack()
        if response and response.startswith("ACK"):
            _, buffer, window = response.split()
            Taille_bloc = int(buffer)
            Taille_fenetre = int(window)
            print(f"Connexion établie avec le serveur {Adress_serveur} (TAILLE_BLOC_MAX={Taille_bloc}, FENETRE={Taille_fenetre})")
            return True
    else:
        print("Erreur lors de l'établissement de la connexion veuillez reessayer en saisissant open <address_ip_du_serveur>")
        client_socket.close()
        client_socket = None
        Adress_serveur = None
        return False # la fonction retourne false en cas d'echec

def terminer_connexion():
    """Ferme la connexion avec le serveur."""
    if Adress_serveur:
        envoi_avec_simulation_de_perte("bye".encode(), Adress_serveur)
        print(f"Déconnexion du serveur {Adress_serveur}")
        client_socket.close()
    else:
        print("Aucune connexion active.")

def lister_fichiers():
    """Demande et affiche la liste des fichiers disponibles sur le serveur."""
    envoi_avec_simulation_de_perte("ls".encode(), Adress_serveur)
    response = reception_ack()
    if response:
        print("Fichiers disponibles:", response)
    else:
        print("Erreur lors de la récupération de la liste des fichiers.")



def recuperer_fichier(filename):
    """Télécharge un fichier depuis le serveur en ignorant les blocs manquants."""
    global Adress_serveur, client_socket, Taille_bloc, Taille_fenetre

    # Envoyer la commande "get" au serveur
    envoi_avec_simulation_de_perte(f"get {filename}".encode(), Adress_serveur)

    # Initialisation des variables
    file_data = {}  # Dictionnaire pour stocker les blocs reçus
    max_seq = -1  # Numéro de séquence maximum reçu
    hasher = hashlib.sha256()  # Pour calculer le hash
    checksum_fichier_original = None  # Initialiser checksum_fichier_original à None


    # Recevoir le checksum du fichier original du serveur
    try:
        client_socket.settimeout(Timeout)
        data, _ = client_socket.recvfrom(Taille_bloc) 
        if data.startswith(b"CHECKSUM:"):
            checksum_fichier_original = data[9:].decode()  # Extraire le checksum après la chaine "CHECKSUM:" qui contient 9 caracteres
            print(f"Checksum du fichier original : {checksum_fichier_original}")
    except socket.timeout:
        print("Aucun checksum reçu du serveur.") 
    finally:
        client_socket.settimeout(None)

    

    while True:
        # Recevoir un paquet du serveur
        try:
            data, _ = client_socket.recvfrom(Taille_bloc + 4)  # 4 octets pour le numéro de séquence
            numero_de_sequence = int.from_bytes(data[:4], byteorder='big')  # Extraire le numéro de séquence
            morceau = data[4:]  # Extraire les données du fichier

            if morceau == b"END":  # Fin du fichier
                print("Fin de transmission reçue !")
                break       

            print(f"Réception du bloc {numero_de_sequence}")

            # Stocker le bloc dans le dictionnaire et si le bloc existe déjà, il est écrasé
            file_data[numero_de_sequence] = morceau

            # Envoi de l'ack à la fin de la taille de la fenêtre
            if (numero_de_sequence + 1) % Taille_fenetre == 0:
                envoi_avec_simulation_de_perte(f"ACK_Block {numero_de_sequence}".encode(), Adress_serveur)
                print("ack envoyé")
            

            # Mettre à jour le numéro de séquence maximum
            if numero_de_sequence > max_seq:
                max_seq = numero_de_sequence

        except socket.timeout:
            print("Timeout: Aucun nouveau bloc reçu. Fin de la transmission.")
            break


    # Réassembler les bloc du fichier dans l'ordre
    nouveau_fichier = "recu_" + filename
    with open(nouveau_fichier, "wb") as f:
        # on Trie les clés du dictionnaire file_data
        for numero_de_sequence in sorted(file_data.keys()):  # Tri des numéros de séquence
            f.write(file_data[numero_de_sequence])

    # Affichage des blocs manquants pour verifier si notre envoi a fonctionner completement
    blocs_manquants = [i for i in range(max_seq + 1) if i not in file_data]
    if blocs_manquants:
        print(f"Blocs manquants : {blocs_manquants}")
    else:
        print("Tous les blocs ont été reçus.")

    

    # Calcul et affichage du checksum du fichier construit 
    hasher = hashlib.sha256()
    with open(nouveau_fichier, "rb") as f:
        while morceau_fichier_construit := f.read(Taille_bloc):
            hasher.update(morceau_fichier_construit)
    checksum_fichier_construit = hasher.hexdigest()

    print(f"Fichier reçu et enregistré sous '{nouveau_fichier}'")
    print(f"Checksum du fichier original (SHA-256) : {checksum_fichier_original}")
    print(f"Checksum du fichier construit (SHA-256) : {checksum_fichier_construit}")

    # Comparaison des checksums
    if checksum_fichier_original is None: # Lorsque le serveur n'a pas pu envoyer le checksum du fichier original
        print("Le checksum du fichier original n'a pas pu etre reçu du serveur à cause d'un problème réseau.")
    elif checksum_fichier_construit == checksum_fichier_original: # Lorsque le serveur a pu envoyer le checksum du fichier original
        print("Les deux checksums correspondent. Le fichier est donc bien recu sans perte de donnees.")
    else: # le serveur a pu envoyer le checksum du fichier original mais il ne correspond pas au checksum du fichier construit par le client
        print("Les deux checksums ne correspondent pas donc il y'a eu perte et le fichier peut être corrompu.")





def main():
    global Adress_serveur, client_socket

    print("Bienvenue dans le shell du client. Tapez 'open <adresse_ip_serveur>' pour vous connecter au serveur.")
    while True:
        command = input("ftp> ").strip()  # Shell de commande pour le client
        if command.startswith("open"):
            try:
                _, ip = command.split()
                if connexion_au_serveur(ip):
                    break  # Sortir de la boucle après une connexion réussie
            except ValueError:
                print("Usage: open <adresse_ip>")
        else:
            print("connectez vous au serveur avec la commande 'open <adresse_ip_serveur>'")

    # Après une connexion réussie, on peut donc saisir les autres commandes à envoyer au serveur"
    while True:
        command = input("ftp> ").strip()
        if command == "ls":
            lister_fichiers()
        elif command.startswith("get"):
            try:
                _, filename = command.split()
                recuperer_fichier(filename)
            except ValueError:
                print("Reessayez: get <filename>")
        elif command == "bye":
            terminer_connexion()
            break
        else:
            print("Commande inconnue.")

if __name__ == "__main__": # Permet d'executer le code si le script est directement appelé
    main()