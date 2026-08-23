# Verset du jour — Instagram automatique

Publie chaque jour, automatiquement et gratuitement, une image avec un verset
biblique **en néerlandais** (Statenvertaling, domaine public) sur fond de
photo de nature (montagne, forêt, plage, étoiles, terre depuis l'espace...),
sur un compte Instagram professionnel — via GitHub Actions + l'API Instagram
(nouveau système "Instagram avec connexion Instagram") + l'API Unsplash +
BijbelAPI. Le token d'accès se renouvelle tout seul chaque jour.

Le verset du jour vient de **BijbelAPI** (bijbelapi.com), une API
néerlandaise gratuite qui pioche dans toute la Bible (Statenvertaling) selon
la date. Si cette API est injoignable un jour, le script bascule
automatiquement sur une petite liste locale de secours (`verses.json`).

## 1. Comptes et accès à préparer (à faire une seule fois)

### a) Compte Instagram professionnel
Paramètres Instagram > Passer à un compte professionnel (Créateur ou
Entreprise). **Pas besoin de Page Facebook liée** avec ce nouveau système.

### b) App Meta for Developers
1. Sur https://developers.facebook.com/apps, crée une app de type
   "Entreprise".
2. Choisis le cas d'usage **"Manage messaging & content on Instagram"**.
3. Une fois l'app créée, si "Instagram API" n'apparaît pas dans le menu de
   gauche, va sur le Dashboard et clique sur "Customize the Manage messaging
   & content on Instagram use case" pour y accéder.
4. Dans le menu, clique sur **"API setup with Instagram login"** (⚠️ pas
   "API setup with Facebook login", c'est un système différent).
5. Note l'**Instagram app ID** et l'**Instagram app secret** affichés en
   haut de cette page (différents de l'App ID/Secret génériques de l'app).

### c) Ajouter la permission de publication
Sur cette même page, section "1. Add required messaging permissions" :
clique sur "Go to permissions and features" et active en plus
**`instagram_business_content_publish`** (les 3 permissions de messagerie
listées par défaut ne suffisent pas pour publier).

### d) Ajouter ton compte comme testeur Instagram
1. Dans le menu de gauche de l'app (en dehors de la section Instagram),
   va dans **App roles > Roles**.
2. Clique sur "Add People", choisis le rôle additionnel **"Instagram
   Tester"**, tape le nom d'utilisateur de ton compte Instagram, et ajoute-le.
3. Sur ton téléphone, ouvre l'app Instagram avec ce compte > Paramètres et
   confidentialité > Applications et sites web > **Invitations de testeur**,
   et accepte l'invitation.

### e) Générer le token d'accès
1. Retourne sur "API setup with Instagram login", section
   **"2. Generate access tokens"**, clique sur "Add account", puis autorise
   ton compte Instagram dans la fenêtre qui s'ouvre.
2. Une fois le compte ajouté au tableau, clique sur **"Generate token"** à
   côté de son nom, puis "Autoriser" dans la fenêtre pop-up.
3. Une page s'ouvre avec le token en texte brut : **c'est déjà un token
   longue durée (60 jours)**, pas besoin de l'échanger davantage. Copie-le.
4. Vérifie qu'il fonctionne en collant cette URL dans le navigateur
   (remplace TON_TOKEN) :
   ```
   https://graph.instagram.com/me?fields=id,username&access_token=TON_TOKEN
   ```
   La réponse doit contenir un `id` (ex: `28203023826003791`) — **c'est
   celui-ci qu'il faut utiliser comme IG_USER_ID**, pas celui affiché dans
   le tableau du dashboard (qui est un ID différent, hérité de l'ancien
   système lié aux Pages Facebook).

### f) Unsplash (photos de nature, gratuit)
1. Crée un compte sur https://unsplash.com/developers
2. Crée une "application" (usage démo, gratuit, 50 requêtes/heure)
3. Note ta **Access Key**

### g) GitHub Personal Access Token (pour l'auto-renouvellement du token)
1. Va sur https://github.com/settings/tokens?type=beta (fine-grained tokens)
2. "Generate new token", limite-le à **ce dépôt uniquement**
3. Dans les permissions du repo, donne accès en **lecture/écriture** à
   "Secrets"
4. Copie ce token

## 2. Déploiement

1. Crée un **dépôt GitHub public**.
2. Pousse tout le contenu de ce dossier dedans.
3. Dans **Settings > Secrets and variables > Actions**, ajoute ces 4 secrets :

   | Secret               | Valeur |
   |----------------------|--------|
   | `IG_USER_ID`          | L'ID obtenu via `graph.instagram.com/me` (étape 1.e.4) |
   | `IG_ACCESS_TOKEN`     | Le token longue durée (étape 1.e.3) |
   | `UNSPLASH_ACCESS_KEY` | Access Key Unsplash |
   | `GH_PAT`              | Le Personal Access Token GitHub (étape 1.g) |

4. Le workflow tourne automatiquement chaque jour à 07h00 UTC (~8-9h à
   Bruxelles). Modifie le `cron` dans `.github/workflows/daily-post.yml`
   pour une autre heure.

## 3. Comment fonctionne le renouvellement automatique du token

Avec ce nouveau système, le renouvellement (`ig_refresh_token`) ne nécessite
plus l'App Secret — seulement le token actuel. Chaque exécution du
workflow :
1. échange le token actuel contre un nouveau, valable 60 jours de plus
   (`refresh_token.py`),
2. écrase le secret `IG_ACCESS_TOKEN` du dépôt avec ce nouveau token,
3. utilise directement ce nouveau token pour publier le post du jour.

Résultat : tant que le workflow s'exécute au moins une fois avant les 60
jours (ce qui est le cas puisqu'il tourne chaque jour), le token ne meurt
jamais.

⚠️ Un token doit avoir **au moins 24h** avant de pouvoir être rafraîchi. Le
tout premier jour après la config initiale, le renouvellement automatique
échouera silencieusement (le script garde l'ancien token, qui reste valide),
puis fonctionnera normalement dès le lendemain.

## 4. Tester manuellement

Onglet **Actions** du dépôt > workflow "Publication quotidienne du verset" >
bouton **Run workflow**.

## 5. Structure du projet

```
.
├── verses.json                      # secours local (français, domaine public)
├── generate_image.py                # génère l'image (photo nature + verset)
├── post_to_instagram.py             # publie l'image sur Instagram
├── refresh_token.py                 # renouvelle automatiquement le token
├── .github/workflows/daily-post.yml # automatisation quotidienne
└── images/verse_of_the_day.png      # image générée (écrasée chaque jour)
```

## 6. Personnalisation

- **Thèmes de photos** : liste `NATURE_QUERIES` dans `generate_image.py`.
- **Couleurs** : `TEXT_COLOR`, `ACCENT_COLOR` dans `generate_image.py`.
- **Légende / hashtags** : ligne `caption = ...` en bas de
  `generate_image.py`.
- **Traduction biblique** : BijbelAPI supporte aussi `hs1917` et `canisius`
  en plus de `sv` (Statenvertaling) — change `"version": "sv"` dans
  `generate_image.py`.

## 7. Vérifier que ça fonctionne bien après le premier run

Dans les logs de l'étape "Générer l'image du jour" (onglet Actions), la
première ligne indique si le verset vient de BijbelAPI ou du secours local.
Dans les logs de "Publier sur Instagram", une réponse contenant un `id` de
publication confirme le succès.

## 8. Limites à connaître

- L'API n'accepte que des **URLs d'images publiques** — d'où le commit +
  push sur GitHub avant publication.
- Compte Instagram limité à ~25 publications via API par 24h (largement
  suffisant pour 1 post/jour).
- Le `GH_PAT` expire selon la durée choisie à sa création (max 1 an) — à
  renouveler à cette échéance (ça ne peut pas s'auto-renouveler).
