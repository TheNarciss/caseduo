# Mettre CaseDuo sur ton iPhone (TestFlight, sans Xcode)

Même principe que SingaSmoke : un Mac de GitHub compile, signe et envoie l'app sur TestFlight. Tu fais une série de réglages, une seule fois, sur les sites d'Apple et dans les secrets GitHub. Aucune de ces valeurs ne passe par un chat.

Ce qui change par rapport à SingaSmoke : CaseDuo a **deux cibles** (l'app et son widget), utilise les **notifications push**, **Sign in with Apple** et un **App Group** partagé entre l'app et le widget. Il y a donc deux App IDs, deux profils et une clé APNs.

## 1. Apple Developer (developer.apple.com → Certificates, Identifiers & Profiles)

| Quoi | Valeur | Où ça sert |
|---|---|---|
| App Group | Identifiers → **+** → App Groups → `group.uk.riskybusinesses.caseduo` | le widget lit ce que l'app y écrit (série, exercices restants, cookie de session) |
| App ID de l'app | Identifiers → **+** → App IDs → App. Description `CaseDuo`, Bundle ID **explicite** `uk.riskybusinesses.caseduo`. Capacités à cocher : **Push Notifications**, **Sign in with Apple**, **App Groups** (puis *Configure* → cocher le groupe ci-dessus) | l'app |
| App ID du widget | Même chemin. Description `CaseDuo Widget`, Bundle ID `uk.riskybusinesses.caseduo.widget`. Capacité : **App Groups** (même groupe) | le widget |
| Clé APNs | Keys → **+** → nom `APNs` → cocher **Apple Push Notifications service (APNs)** → télécharger le `.p8` (une seule fois) et noter son **Key ID**. Une clé vaut pour toutes les apps du compte : si tu en as déjà une, réutilise-la | le backend (section 4) |
| Profil de l'app | Profiles → **+** → Distribution → **App Store Connect** → App ID `CaseDuo` → le **même certificat Apple Distribution que Tangent et SingaSmoke** → nom `CaseDuo App Store` → télécharger | secret `IOS_PROVISIONING_PROFILE_B64` |
| Profil du widget | Même chemin, App ID `CaseDuo Widget`, nom `CaseDuo Widget App Store` | secret `IOS_WIDGET_PROVISIONING_PROFILE_B64` |

Si tu ajoutes une capacité à un App ID **après** avoir créé son profil, régénère le profil (Edit → Save), sinon la signature échoue.

Pour Sign in with Apple côté serveur, le backend vérifie l'`id_token` contre le bundle `uk.riskybusinesses.caseduo` (`APPLE_BUNDLE_ID` dans `backend/.env`). Pas de Services ID à créer : CaseDuo n'a pas de site.

## 2. App Store Connect (appstoreconnect.apple.com)

Apps → **+** → Nouvelle app :
- plateforme **iOS**, nom **CaseDuo**,
- langue principale **Français**, bundle ID `uk.riskybusinesses.caseduo`, SKU libre (`caseduo`), accès complet.

Rien d'autre pour TestFlight. Le chiffrement est déjà réglé (`ITSAppUsesNonExemptEncryption = NO`).

Pour la soumission à la revue, plus tard :
- **Informations** : catégorie Éducation, classification 4+, URL de confidentialité `https://caseduo.riskybusinesses.uk/legal/privacy.html`, URL d'assistance `https://caseduo.riskybusinesses.uk/legal/about.html`. Les textes de la fiche sont dans `ios/fastlane/metadata/fr-FR/`.
- **Confidentialité de l'app** : données collectées, liées à l'identité, sans suivi : adresse e-mail, nom, contenu utilisateur (réponses écrites ou dictées), identifiant utilisateur, identifiant d'appareil (jeton push). Le manifeste `PrivacyInfo.xcprivacy` déclare la même chose.
- **Captures** : iPhone 6,7" (1290 × 2796). Les captures du workflow (simulateur, données de démo) donnent l'aperçu ; refais-les sur le simulateur 6,7" pour la fiche.
- **Notes pour la revue** : le texte de `ios/fastlane/metadata/review_information/notes.txt`, et dans les champs *Sign-in information* : `demo@riskybusinesses.uk` et son mot de passe (section 5).

## 3. Les secrets GitHub

Huit secrets dans **TheNarciss/caseduo → Settings → Secrets and variables → Actions**. Six sont les mêmes valeurs que dans Tangent et SingaSmoke (GitHub ne permet pas de les relire : reprends-les depuis tes fichiers) ; les deux profils sont propres à CaseDuo.

Depuis la VM, dans le dossier où sont les fichiers (`gh auth status` doit être connecté) :

```bash
R=TheNarciss/caseduo
gh secret set IOS_PROVISIONING_PROFILE_B64        -R $R --body "$(base64 -w0 CaseDuo_App_Store.mobileprovision)"
gh secret set IOS_WIDGET_PROVISIONING_PROFILE_B64 -R $R --body "$(base64 -w0 CaseDuo_Widget_App_Store.mobileprovision)"
gh secret set IOS_CERTIFICATE_P12_B64             -R $R --body "$(base64 -w0 distribution.p12)"
gh secret set APPSTORE_API_KEY_P8_B64             -R $R --body "$(base64 -w0 AuthKey_XXXXXXXXXX.p8)"
# Ces quatre-là demandent la valeur au clavier (rien ne reste dans l'historique) :
gh secret set IOS_CERTIFICATE_PASSWORD -R $R
gh secret set APPLE_TEAM_ID            -R $R
gh secret set APPSTORE_API_KEY_ID      -R $R
gh secret set APPSTORE_API_ISSUER_ID   -R $R
gh secret list -R $R
```

Plus de `.p12` ou de clé API ? Les recettes sont dans `docs/testflight.md` de SingaSmoke (régénérer le certificat depuis la VM avec `openssl … -legacy`, recréer une clé App Manager), elles valent à l'identique.

## 4. La clé APNs sur la VM

Le backend envoie le rappel de 20 h et le message d'au revoir après 7 jours d'absence. Dans `backend/.env` sur la VM :

```bash
APNS_TEAM_ID=XXXXXXXXXX            # le Team ID
APNS_KEY_ID=YYYYYYYYYY             # le Key ID de la clé APNs
APNS_PRIVATE_KEY_B64=$(base64 -w0 AuthKey_YYYYYYYYYY.p8)
APNS_BUNDLE_ID=uk.riskybusinesses.caseduo
```

Puis `docker compose -f docker-compose.yml -f docker-compose.prod.yml restart backend`. L'app envoie son jeton avec son environnement : `sandbox` pour une build Xcode, `production` pour TestFlight et l'App Store ; le backend choisit le serveur APNs en conséquence.

## 5. Le compte de démonstration (revue Apple)

Tangent s'est fait refuser pour un compte de démo cassé : ici, il se vérifie avant chaque soumission.

1. Sur la VM, créer ou rafraîchir le compte (même commande que Tangent, voir le README du backend) :
   `DEMO_EMAIL=demo@riskybusinesses.uk DEMO_PASSWORD='…' python -m app.demo` dans le conteneur backend.
2. Sur ton iPhone (build TestFlight), **se déconnecter puis se connecter avec ce compte**, ouvrir un exercice, répondre, vérifier que la note arrive. Vérifier aussi qu'Historique, Ligue et Profil ont du contenu.
3. Recopier le mot de passe dans App Store Connect → la version → *Sign-in information*.

Le compte n'est pas administrateur et ne dépend d'aucun service extérieur : pas de banque, pas de Google, pas d'abonnement.

## 6. Construire et installer

- **Automatique** : chaque push sur `main` qui touche `ios/` compile et envoie un build sur TestFlight.
- **À la main, depuis la VM** :

  ```bash
  gh workflow run ios.yml -R TheNarciss/caseduo -f testflight=true
  gh run watch -R TheNarciss/caseduo
  ```

- **Sur l'iPhone** : App Store Connect → CaseDuo → TestFlight → Tests internes → ajoute-toi, puis installe depuis l'app **TestFlight**. Le build apparaît 5 à 30 minutes après l'envoi.

Un build TestFlight expire au bout de 90 jours : relance le workflow avant.

## 7. Développer contre un backend local

Les builds Debug acceptent un argument de lancement : dans Xcode, *Edit Scheme → Run → Arguments* : `-apiBaseURL http://localhost:8000/api` (le simulateur voit le Mac comme `localhost`). `-uiDemo YES` lance l'app avec des données de démonstration, sans réseau ni connexion (c'est ce que font les captures de la CI).

## Quand ça coince

| Message dans le job | Cause |
|---|---|
| `TestFlight ignoré : secrets manquants` | un des huit secrets n'existe pas (la liste est dans le message) |
| `No profiles for 'uk.riskybusinesses.caseduo.widget'` | le profil du widget manque, ou ce n'est pas un profil App Store |
| `Provisioning profile … doesn't include the aps-environment entitlement` | Push Notifications n'était pas coché sur l'App ID quand le profil a été créé : régénère le profil |
| `… doesn't support the App Groups capability` | App Groups non coché (ou groupe non sélectionné) sur l'un des deux App IDs |
| `Provisioning profile … doesn't include signing certificate` | profil fait avec un autre certificat que celui du `.p12` |
| `No suitable application records were found` | l'app n'existe pas encore dans App Store Connect (étape 2) |
| `The bundle version must be higher` | un build avec ce numéro existe déjà ; relance, le numéro suit le compteur d'exécutions |
