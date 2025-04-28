# Instructions d'utilisation du projet

## 1. Lancer le serveur

Exécutez le script du **serveur** en premier :

```bash
python serveur.py
```

## 2. Lancer le client
Dans un autre terminal ou une autre machine, exécutez le script du client :

```bash
python client.py
```
## 3. Se connecter au serveur
Dans le terminal du client, tapez la commande suivante pour ouvrir une connexion :

```bash
open <adresse_ip_serveur>
```
## 4. Voir la liste des fichiers disponibles
Une fois connecté, vous pouvez afficher la liste des fichiers disponibles sur le serveur avec la commande :

```bash
ls
```
Notes :
Les fichiers disponibles sont stockés sur le serveur dans le dossier fichiers_serveur.

## 5. Telecharger un fichier
Pour telecharger un fichier, tapez la commande suivante :
```bash
get <nom_du_fichier.extension>
```
## 6. Fermer la connexion
Lorsque vous avez terminé, tapez la commande suivante pour fermer proprement la connexion :

```bash
bye
```