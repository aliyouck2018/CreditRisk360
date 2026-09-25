Tu es un développeur senior qui va mettre à jour le projet CreditRisk360 (Flask + PostgreSQL/Supabase + Jinja2). 
Fais toutes les modifications ci-dessous, dans le code de l'application ET dans le README.md. 
Ne casse aucune fonctionnalité existante. Si une modification touche plusieurs fichiers (ex: nom d'entreprise en dur dans plusieurs templates), applique-la partout où le terme apparaît.

=== 1. RENOMMAGE ENTITÉS FICTIVES ===
- Remplace partout "Bantu Scoring SA" et "Bantu Scoring SA" par "Bantu Scoring SA".
- Remplace partout "Alex Liyouck" par "Alex Liyouck".
- Cherche dans les templates HTML/Jinja, dans app/, dans le seed (seed_supabase.py) et dans le README/cahier des charges toute occurrence de ces deux noms (y compris variantes de casse ou d'initiales, ex: "AL" pour Alex Liyouck → à remplacer par les initiales correspondantes "AL").
- Vérifie qu'aucune mention résiduelle de "Bantu Scoring SA" ne subsiste nulle part dans le repo (grep global sur "Bantu Scoring SA" et "Alex Liyouck").
- Le README doit clairement indiquer que "Bantu Scoring SA" est une entité fictive, sans lien avec une société réelle, créée uniquement pour les besoins de la démo.

=== 2. CORRECTIONS DE BUGS DANS L'APPLICATION ===
- Corrige l'affichage des pourcentages sur la page /methodology : actuellement certains textes affichent "2 %%", "25 %%", "100 %%" au lieu de "2 %", "25 %", "100 %" (probable erreur d'échappement dans un format string Python, ex: %% au lieu de % dans une f-string ou un .format()). Corrige la cause à la racine dans le code, pas seulement le texte affiché.
- Corrige le lien de la carte "Rapports PDF" sur la page d'accueil, qui pointe actuellement vers /methodology au lieu de la bonne route (identifie la route correcte du module Rapports PDF dans app/routes/ et corrige le lien).
- Ajoute une courte note explicative sur le tableau de bord ou sur /methodology clarifiant pourquoi le Ratio NPL (4.6%) et le Taux de paiement (99.4%) peuvent coexister (le NPL porte sur l'encours total, le taux de paiement sur les échéances dues à date — ce ne sont pas les mêmes dénominateurs).
- Vérifie la cohérence entre les chiffres affichés sur le dashboard (12 021 emprunteurs, 16 771 prêts actifs + 2 519 clôturés = 19 290 prêts) et les chiffres annoncés dans le README (12 000 emprunteurs, 20 000 prêts). Si l'écart vient des scénarios/anomalies injectés par seed_supabase.py, documente-le clairement dans le README section "Génération de données". Sinon corrige l'incohérence.

=== 3. CORRECTIONS TEXTUELLES DANS LE README.md ===
Corrige ces coquilles :
- "ngarde-fous" → "garde-fous"
- "dentro de" → "dans"
- "démarrage rapid" → "démarrage rapide"
- "aggégations" → "agrégations"
- "expliabilité" → "explicabilité"
- "amortisseur mensuel" → "amortissement mensuel"
- "consultations bureautiques" → "consultations bureau de crédit"
- "destruction analytique" → "exploration analytique" (dans la description de l'Analyste IA)
Aligne aussi la version Python annoncée dans le badge (actuellement "Python 3.14+") avec celle indiquée dans la stack technique ("Python 3.11+") — utilise la version réellement utilisée par le projet.

=== 4. RESTRUCTURATION DE LA PARTIE HAUTE DU README ===
Remplace l'introduction actuelle par une structure de ce type (en gardant le ton et la langue française, ajuste les chiffres si les vrais diffèrent) :

- Titre + badges (inchangés)
- Une ligne avec : lien "▶ Démo en ligne" vers https://credit-risk360-smoky.vercel.app, mention "Données 100% synthétiques", mention "Projet personnel, non affilié à une institution"
- Un court paragraphe de positionnement (1-2 phrases) sur ce que fait l'app
- Une section "Résultats clés" en 3-4 puces basées sur les scénarios réellement injectés par le seed (dérive BTP Cameroun, dépassements de limites au Tchad, cohortes 2025 dégradées, etc. — reprends les vrais éléments du seed_supabase.py)
- Une ligne "Compétences mises en œuvre" citant SQL, définition de KPI, qualité des données, scoring, tests pytest, déploiement (Flask, Supabase, Vercel)
- Puis seulement ensuite : Démarrage rapide, Aperçu du produit, etc. (structure existante conservée)

Déplace les 9 captures d'écran individuelles dans une section repliable en fin de README, en utilisant la syntaxe HTML <details><summary>Voir toutes les captures d'écran</summary> ... </details>. Garde une seule image (le dashboard) visible en haut, juste après le bloc d'intro.

=== 5. CLARTÉ SUR LES LIMITES TECHNIQUES ===
Dans la section "3. Fonctionnalités", pour l'entrée "Analyste IA (W3)", ajoute une précision explicite dès la première ligne indiquant que le moteur NL2SQL est un traducteur heuristique par règles (pas un LLM), remplaçable par un LLM distant — ne laisse pas cette info seulement dans "Limites connues" en bas de page.
Ajoute une phrase dans la section Scoring précisant que les pondérations sont fixées manuellement (non calibrées par apprentissage automatique), cohérent avec l'objectif d'explicabilité plutôt que de précision prédictive.

=== 6. HYGIÈNE DU DÉPÔT ===
- Ajoute un fichier .env.example à la racine avec les variables attendues (SECRET_KEY, DATABASE_URL) avec des valeurs factices.
- Ajoute un fichier LICENSE avec la licence MIT (si aucune licence n'existe déjà).
- Vérifie qu'aucun secret réel (mot de passe, URL Supabase avec identifiants) n'apparaît dans le code, les fichiers de config ou l'historique récent des commits. Si tu en trouves, signale-le clairement sans l'afficher en clair dans ta réponse.
- Déplace cahier_des_charges_creditrisk360.md dans un dossier docs/ s'il n'y est pas déjà.
- Vérifie s'il y a duplication entre les dossiers screenshots/ et docs/img/ ; si oui, garde un seul dossier (docs/img/) et supprime l'autre, en mettant à jour tous les liens du README en conséquence.

=== 7. AJOUTS TECHNIQUES POUR LE README ===
- Ajoute un diagramme du schéma de base de données en syntaxe Mermaid (```mermaid erDiagram ... ```) représentant les 8 tables et leurs relations principales, à partir du contenu de schema.sql.
- Ajoute une section "Décisions d'analyse" (courte, 4-5 puces) expliquant : pourquoi l'exposition est l'encours restant dû et non le capital initial, pourquoi le seuil de défaut est fixé à 90 jours, comment est défini un "dossier vierge", pourquoi les limites de concentration sont à 25%/2%.
- Ajoute 2 à 3 extraits de requêtes SQL réelles tirées des vues du projet (ex: calcul du NPL depuis v_kpi_monthly, ou une requête d'analyse de vintage), avec une phrase d'explication pour chacune.

=== CONTRAINTES ===
- Ne modifie pas la logique métier des calculs (NPL, scoring, HHI, etc.), seulement leur présentation/documentation, sauf pour le bug du double "%%" qui doit être corrigé dans le code.
- Garde tout le contenu en français.
- À la fin, produis un résumé de tous les fichiers modifiés et pourquoi.