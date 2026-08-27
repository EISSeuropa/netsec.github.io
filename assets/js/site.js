/* NetSec — shared site script
   ────────────────────────────────────────────────────────────────
   Loaded by every page. Each block is guarded so it no-ops when the
   relevant DOM element isn't present, so additional pages can opt in
   to whichever features they need. */
(function () {
  'use strict';

  /* String catalog + window.netsecT() helper — defined first so that
     every later block (theme toggle, mobile menu, member directory)
     can call it without ordering pitfalls. The catalog lives here as
     a single source of truth; page-specific scripts read from it via
     the global helper exposed at the bottom of this block. */
  const I18N = {
    en: {},
    fr: {
      'Action Chair': "Président·e de l'Action",
      'Action Vice-Chair': "Vice-président·e de l'Action",
      'Grant Holder Scientific Representative': 'Représentant·e scientifique du porteur de subvention',
      'Science Communication Coordinator': 'Coordinateur·rice communication scientifique',
      'Grant Awarding Coordinator': "Coordinateur·rice d'attribution des subventions",
      'Grant Awarding Coordinator Co-lead': "Coordinateur·rice adjoint·e d'attribution",
      'WG1 Leader': 'Responsable WG1',
      'WG2 Leader': 'Responsable WG2',
      'WG3 Leader': 'Responsable WG3',
      'WG4 Leader': 'Responsable WG4',
      'WG1 Co-Leader': 'Co-responsable WG1',
      'WG2 Co-Leader': 'Co-responsable WG2',
      'WG3 Co-Leader': 'Co-responsable WG3',
      'WG4 Co-Leader': 'Co-responsable WG4',
      'Management Committee': 'Comité de gestion',
      'Event': 'Événement',
      'Publication': 'Publication',
      'Announcement': 'Annonce',
      'Read more': 'Lire la suite',
      'Read less': 'Réduire',
      'Working Group participant': 'Participant·e au groupe de travail',
      'Bio coming soon.': 'Biographie à venir.',
      'View full profile': 'Voir le profil complet',
      'View profile': 'Voir le profil',
      'Quick look': 'Aperçu',
      'Member profile': 'Profil du membre',
      'Show more': 'Voir plus',
      'Show less': 'Voir moins',
      'member': 'membre',
      'members': 'membres',
      'Show {0} members': 'Afficher {0} membres',
      'Remove filter': 'Retirer le filtre',
      'Switch to dark mode': 'Basculer le mode sombre',
      'Switch to light mode': 'Basculer le mode clair',
      'Unable to load network directory.': "Impossible de charger l'annuaire du réseau.",
      'Please refresh, or use the {0}.': 'Veuillez recharger ou utiliser le {0}.',
      'contact page': 'formulaire de contact',
      'Research interests': 'Domaines de recherche',
      'Research themes': 'Thèmes de recherche',
      'Research regions': 'Régions de recherche',
      'Works on similar topics': 'Travaille sur des thèmes proches',
      'See everyone in these themes': 'Voir tout le monde sur ces thèmes',
      'Mentors on similar topics': 'Mentor·es sur des thèmes proches',
      'See these mentors in the directory': 'Voir ces mentor·es dans l’annuaire',
      'In the EISS Anthology': "Dans l'Anthologie de l'EISS",
      'Show all': 'Tout afficher',
      'Show fewer': 'Réduire',
      'Clear': 'Effacer',
      'Close': 'Fermer',
      'Filter by research interest': 'Filtrer par domaine de recherche',
      'Directory last updated {0}.': 'Annuaire mis à jour le {0}.',
      'Available to mentor': 'Disponible comme mentor',
      'Seeking mentorship': 'En recherche de mentorat',
      'Mentoring, at capacity': 'Mentor, plus de disponibilité',
      'Recent publications': 'Publications récentes',
      'Can host STSM visitors': 'Peut accueillir des visiteurs STSM',
      'Open to hosting STSM visitors': 'Ouvert à accueillir des visiteurs STSM',
      'Mentorship matching': 'Mise en relation pour le mentorat',
      'Mentoring in the network is informal. Introduce yourself directly and say what you are looking for. If you are unsure where to start, your Working Group lead can help make an introduction.': 'Le mentorat dans le réseau est informel. Présentez-vous directement et indiquez ce que vous recherchez. Si vous ne savez pas par où commencer, le responsable de votre groupe de travail peut faciliter une mise en relation.',
      'Offering mentorship': 'Propose du mentorat',
      'No one here yet.': 'Personne ici pour le moment.',
      'No one in your selected research areas yet.': 'Personne dans vos domaines sélectionnés pour le moment.',
      'Also show members offering mentorship': 'Afficher aussi les membres proposant du mentorat',
      'Also show members seeking mentorship': 'Afficher aussi les membres en recherche de mentorat',
      'In your selected research areas': 'Dans vos domaines sélectionnés',
      '{offer} offering mentoring, {seek} seeking a mentor': '{offer} proposant du mentorat, {seek} à la recherche d’un·e mentor·e',
      'Shared research areas': 'Domaines de recherche partagés',
      'Order for my career stage': 'Classer selon mon niveau de carrière',
      // Warm contact intro (#1171). The same texts are baked build-time into
      // the profile pages by scripts/build-profile-pages.py (SCAFFOLDS); its
      // test_scaffold_parity fails if the two homes drift. Edit both.
      'Introduce yourself by email': 'Se présenter par e-mail',
      'Mentorship enquiry via the NetSec directory': "Demande de mentorat via l'annuaire NetSec",
      'Mentorship via the NetSec directory': "Mentorat via l'annuaire NetSec",
      'STSM hosting enquiry via the NetSec directory': "Demande d'accueil STSM via l'annuaire NetSec",
      ' We share these research areas: {areas}.': ' Nous partageons ces domaines de recherche : {areas}.',
      ' I was drawn by your work on {areas}.': ' Vos travaux sur {areas} ont retenu mon attention.',
      "Dear {name},\n\nI found your profile in the NetSec directory.{areas_line}\n\nAbout me: [your name, career stage, institution, and a line on your research]\nWhat I am hoping for: [advice on publishing, a career conversation, feedback on a draft]\n\nWould you be open to a short online conversation in the coming weeks?\n\nBest regards,\n[your name]":
        "Bonjour {name},\n\nJ'ai trouvé votre profil dans l'annuaire NetSec.{areas_line}\n\nQui je suis : [votre nom, niveau de carrière, institution, et une ligne sur vos recherches]\nCe que je recherche : [des conseils de publication, un échange sur la carrière, un retour sur un texte]\n\nSeriez-vous ouvert·e à un court échange en ligne dans les prochaines semaines ?\n\nBien cordialement,\n[votre nom]",
      "Dear {name},\n\nI saw in the NetSec directory that you are seeking mentorship.{areas_line}\n\nAbout me: [your name, role, institution, and the areas where you could help]\n\nIf useful, I would be happy to have a short conversation about your goals.\n\nBest regards,\n[your name]":
        "Bonjour {name},\n\nJ'ai vu dans l'annuaire NetSec que vous recherchez un mentorat.{areas_line}\n\nQui je suis : [votre nom, fonction, institution, et les domaines où vous pourriez aider]\n\nSi cela vous est utile, je serais heureux·se d'échanger brièvement sur vos objectifs.\n\nBien cordialement,\n[votre nom]",
      "Dear {name},\n\nI found you in the NetSec directory as a possible STSM host.{areas_line}\n\nAbout me: [your name, career stage, institution]\nVisit idea: [topic and rough dates]\n\nAn STSM is a short funded research visit under the NetSec COST Action. If the fit looks right I would apply through e-COST. Would you be open to discussing it?\n\nBest regards,\n[your name]":
        "Bonjour {name},\n\nJe vous ai trouvé·e dans l'annuaire NetSec comme hôte STSM possible.{areas_line}\n\nQui je suis : [votre nom, niveau de carrière, institution]\nIdée de visite : [sujet et dates approximatives]\n\nUne STSM est une courte visite de recherche financée par l'Action COST NetSec. Si cela correspond, je déposerais une candidature via e-COST. Seriez-vous ouvert·e à en discuter ?\n\nBien cordialement,\n[votre nom]",
      'Most relevant first': 'Les plus pertinent·es en premier',
      'Any': 'Indifférent',
      'Doctoral': 'Doctorat',
      'Early-career': 'Début de carrière',
      'Mid-career': 'Milieu de carrière',
      'Senior': 'Confirmé·e',
      'Tip: add a research-theme or region filter above to narrow these lists to your own research area.': 'Astuce : ajoutez un filtre par thème de recherche ou région ci-dessus pour restreindre ces listes à votre propre domaine.',
      'Show people outside your selected research areas': 'Voir les personnes hors de vos domaines sélectionnés',
      'Show only your selected research areas': 'Afficher uniquement vos domaines sélectionnés',
      // ── Mentorship wizard + grid (W5) ──
      // The sentence scaffold is per-locale: the French connectives recast the
      // English participle ("looking for") as a coordinated finite clause
      // ("et je cherche") so the line reads naturally around the tokens.
      'I am': 'Je suis',
      'looking for': 'et je cherche',
      'in': 'en',
      'a doctoral researcher': "un·e doctorant·e",
      'an early-career researcher': 'un·e chercheur·euse en début de carrière',
      'a mid-career researcher': 'un·e chercheur·euse en milieu de carrière',
      'a senior researcher': 'un·e chercheur·euse confirmé·e',
      'a mentor': 'un·e mentor·e',
      'a mentee': 'un·e mentoré·e',
      'choose your stage': 'choisissez votre niveau',
      'Career stage': 'Niveau de carrière',
      'Looking for': 'Recherche',
      'Research area': 'Domaine de recherche',
      'choose a research area': 'choisissez un domaine',
      '{n} offering': '{n} proposent',
      '{n} seeking': '{n} en recherche',
      'Guided': 'Guidé',
      'Browse all': 'Tout parcourir',
      'Mentorship view': 'Affichage du mentorat',
      'Matches update as you choose. Your stage and areas stay on this page only.': 'Les correspondances se mettent à jour au fil de vos choix. Votre niveau et vos domaines restent sur cette page uniquement.',
      'Mentoring in the network is informal: introduce yourself directly and say what you are looking for. Nothing you choose here is stored.': "Le mentorat dans le réseau est informel : présentez-vous directement et indiquez ce que vous recherchez. Rien de ce que vous choisissez ici n'est enregistré.",
      'Your closest matches': 'Vos meilleures correspondances',
      'shared research areas first, then a mentor one or two steps ahead of you': 'les domaines de recherche partagés d’abord, puis un·e mentor·e une ou deux étapes devant vous',
      'shared research areas first, then someone a step or two earlier in their career': 'les domaines de recherche partagés d’abord, puis une personne une ou deux étapes plus tôt dans sa carrière',
      'Best match': 'Meilleure correspondance',
      'No. 2': 'N° 2',
      'No. 3': 'N° 3',
      '{first} and {second}': '{first} et {second}',
      'Works on {areas}.': 'Travaille sur {areas}.',
      'Works on {areas} and is a near peer, recently in your shoes.': 'Travaille sur {areas} et se situe à un niveau proche du vôtre, récemment à votre place.',
      'Works on {areas} and is one step ahead of you, the gap the mentoring literature favours.': "Travaille sur {areas} et se situe une étape devant vous, l'écart que privilégie la littérature sur le mentorat.",
      'Works on {areas} and sits a couple of steps ahead of you.': 'Travaille sur {areas} et se situe deux étapes devant vous.',
      'Works on {areas} and is earlier in their career, someone you could support.': 'Travaille sur {areas} et se trouve plus tôt dans sa carrière, une personne que vous pourriez soutenir.',
      'Introduce yourself': 'Se présenter',
      'Profile': 'Profil',
      'See all {n} offering mentorship': 'Voir les {n} membres proposant du mentorat',
      'See all {n} seeking mentorship': 'Voir les {n} membres en recherche de mentorat',
      '{n} people are seeking mentorship in your area, could you mentor one of them?': '{n} personnes recherchent un mentorat dans votre domaine, pourriez-vous en accompagner une ?',
      '{n} people are offering mentorship in your area, could one of them help you?': "{n} personnes proposent un mentorat dans votre domaine, l'une d'elles pourrait-elle vous aider ?",
      'Narrow the matches': 'Affiner les correspondances',
      'Show people in:': 'Afficher les personnes en :',
      'All themes…': 'Tous les thèmes…',
      'Order for my stage:': 'Classer selon mon niveau :',
      'Offering mentorship in your area ({n})': 'Proposent du mentorat dans votre domaine ({n})',
      'Seeking mentorship in your area ({n})': 'En recherche de mentorat dans votre domaine ({n})',
      'Offering mentorship ({n})': 'Proposent du mentorat ({n})',
      'Seeking mentorship ({n})': 'En recherche de mentorat ({n})',
      'Most relevant first: shared research areas, then a mentor one or two steps ahead of you': 'Les plus pertinent·es d’abord : domaines de recherche partagés, puis un·e mentor·e une ou deux étapes devant vous',
      'Most relevant first: shared research areas, then someone a step or two earlier in their career': 'Les plus pertinent·es d’abord : domaines de recherche partagés, puis une personne une ou deux étapes plus tôt dans sa carrière',
      'Show all {n} offering mentorship': 'Afficher les {n} proposant du mentorat',
      'Show all {n} seeking mentorship': 'Afficher les {n} en recherche de mentorat',
      'Near peer': 'Niveau proche',
      '1 step ahead': 'Une étape devant',
      '2 steps ahead': 'Deux étapes devant',
      '{n} steps ahead': '{n} étapes devant',
      'Founding contributor': 'Contributeur fondateur',
      'Listed in the COST Open Call proposal OC-2024-1-27931': "Mentionné·e dans la proposition de l'Appel ouvert COST OC-2024-1-27931",
      'Research themes': 'Thèmes de recherche',
      'Filter by research theme': 'Filtrer par thème de recherche',
      'Foreign policy and diplomacy': 'Politique étrangère et diplomatie',
      'Security and defence': 'Sécurité et défense',
      'Strategy and deterrence': 'Stratégie et dissuasion',
      'European and transatlantic security order': 'Ordre de sécurité européen et transatlantique',
      'Intelligence, information and influence': 'Renseignement, information et influence',
      'Identity, narratives and ideational security': 'Identité, récits et sécurité idéationnelle',
      'Cyber and emerging technology': 'Cyber et technologies émergentes',
      'Economic security and geoeconomics': 'Sécurité économique et géoéconomie',
      'Transnational and human security': 'Sécurité transnationale et humaine',
      'Peace, mediation and reconciliation': 'Paix, médiation et réconciliation',
      'Theory and methods': 'Théorie et méthodes',
      'EU, UN and other international organisations': 'UE, ONU et autres organisations internationales',
      'Crisis management and critical systems resilience': 'Gestion de crise et résilience des systèmes critiques',
      'Political psychology, public opinion and decision-making': 'Psychologie politique, opinion publique et prise de décision',
      'Research regions': 'Régions de recherche',
      'Filter by research region': 'Filtrer par région de recherche',
      'Europe': 'Europe',
      'Europe - Western Balkans': 'Europe - Balkans occidentaux',
      'Europe - Eastern neighbours / Russia': 'Europe - Voisinage oriental / Russie',
      'Middle East and North Africa': 'Moyen-Orient et Afrique du Nord',
      'Africa': 'Afrique',
      'Asia': 'Asie',
      'The Americas': 'Amériques',
      'Global and cross-regional': 'Mondial et transrégional',
      'Search': 'Recherche',
      'Jump to the join form': 'Aller au formulaire',
      'Anyone can join': 'Tout le monde peut rejoindre',
      'Filter by working group or Management Committee role': 'Filtres par groupe de travail ou rôle au Comité de gestion',
      'Filter by mentorship': 'Filtrer par mentorat',
      'Filter by STSM hosting': 'Filtrer par accueil STSM',
      'Filter by country': 'Filtrer par pays',
      'Switch card density': 'Changer la densité des cartes',
      'Filters': 'Filtres',
      'Free-text search across names, affiliations, and countries. Combines with the filters.': 'Recherche en texte libre sur les noms, affiliations et pays. Se combine avec les filtres.',
      'The + button takes you straight to the join card at the foot of this page.': 'Le bouton + vous amène directement à la carte « Rejoindre le réseau » au pied de la page.',
      'Add yourself via the form here. About three minutes to fill in. Cards appear on this page within a week of submission.': 'Inscrivez-vous via le formulaire ci-dessous. Environ trois minutes. Les cartes apparaissent sur cette page sous une semaine après soumission.',
      'WG1–WG4 filter by Working Group. The Management Committee chip surfaces only Management Committee representatives.': "WG1–4 filtrent par groupe de travail. La pastille « Comité de gestion » n'affiche que les représentant·es du Comité de gestion.",
      'These chips group the directory by broad research theme, clustering people who work in the same area. Tap to narrow the list, tap more to widen the match. The keyword pills on each card are clickable too, and your selection lives in the URL so a filtered view is shareable.': "Ces pastilles regroupent l'annuaire par grand thème de recherche, en rassemblant les personnes qui travaillent dans le même domaine. Cliquez pour restreindre la liste, cliquez davantage pour élargir la correspondance. Les pastilles de mot-clé sur chaque fiche sont cliquables aussi, et votre sélection vit dans l'URL : une vue filtrée se partage en copiant l'adresse.",
      'A second, geographic axis: the parts of the world members focus their research on, not where they are based. Combine it with the themes above to narrow by both.': "Un second axe, géographique : les régions du monde sur lesquelles les membres concentrent leurs recherches, et non là où elles et ils sont basés. Combinez-le avec les thèmes ci-dessus pour restreindre selon les deux.",
      'Members can flag that they are available to mentor early-career researchers, or seeking mentorship themselves. Use these chips to find them. This row appears once at least one member has opted in.': "Les membres peuvent indiquer qu'ils sont disponibles comme mentor pour les chercheur·euses en début de carrière, ou en recherche de mentorat. Utilisez ces pastilles pour les trouver. Cette rangée apparaît dès qu'au moins un membre s'est inscrit.",
      'A Short-Term Scientific Mission is a funded research visit to another member’s institution. This chip surfaces the members who have offered to host STSM visitors.': "Une mission scientifique de courte durée (STSM) est une visite de recherche financée dans l'institution d'un autre membre. Cette pastille fait ressortir les membres qui ont proposé d'accueillir des visiteur·euses STSM.",
      'Detailed shows photos and bios. Compact shows initials, name, affiliation and Working-Group chips, three to a row. Your choice is remembered. Phones always use compact cards.': 'La vue détaillée montre photos et bios. La vue compacte montre initiales, nom, affiliation et pastilles de groupe, trois par ligne. Votre choix est conservé. Les téléphones utilisent toujours les cartes compactes.',
      'Tap Filters to narrow the directory by working group, research theme, research region, mentorship, or STSM hosting. The badge shows how many filters are active.': "Touchez « Filtres » pour restreindre l'annuaire par groupe de travail, thème de recherche, région de recherche, mentorat ou accueil STSM. Le badge indique le nombre de filtres actifs.",
      'Next': 'Suivant',
      'Back': 'Précédent',
      'Done': 'Terminer',
      'Skip': 'Ignorer',
      'Step %1 of %2': 'Étape %1 sur %2',
      'Close tour': 'Fermer la visite',
      // NetSec Network Map (#764): the controls, the statistics strip, and the
      // hover card, all injected by assets/js/network-map.js. The 14 theme
      // names the hub chips carry are already translated further up, since
      // the directory's theme filter uses the same keys.
      'Working Groups': 'Groupes de travail',
      // The four WG titles, drawn on the canvas under each hub. Lifted from
      // the hand-translated headings on working-groups.fr.html so the two
      // surfaces cannot disagree.
      'Building the Network': 'Bâtir le réseau',
      'Transfer of Knowledge': 'Transfert des connaissances',
      'Fostering the Next Generation of Scholars': 'Former la prochaine génération de chercheurs',
      'Inclusion, Representativeness & Ethics': 'Inclusion, représentativité et éthique',
      'ESSC co-panels': 'Panels partagés ESSC',
      'Edition': 'Édition',
      'All editions': 'Toutes les éditions',
      'Filter co-panels by conference edition': 'Filtrer les panels partagés par édition de la conférence',
      'Mentorship offers & requests': 'Offres et demandes de mentorat',
      'Co-authored outputs': 'Publications co-signées',
      // The filter disclosure's own summary, and the list under the map.
      'showing all {n}': 'tous les {n} affichés',
      'showing {n} of {m}': '{n} sur {m} affichés',
      'Showing {n} of {m} people.': '{n} personnes affichées sur {m}.',
      // Find, and the answer it gives (#1642).
      'No one on the map matches {q}.': 'Personne sur la carte ne correspond à {q}.',
      '{name} is on the map but hidden by the filters in use.': '{name} est sur la carte, mais les filtres actifs le ou la masquent.',
      'Showing {name}.': '{name} est mis en évidence.',
      'That link filtered the map to hubs it does not hold, so the whole map is shown.': 'Ce lien filtrait la carte sur des pôles qu’elle ne contient pas, la carte entière est donc affichée.',
      'See this member on the Network Map': 'Voir ce membre sur la carte du réseau',
      // Bulk actions on the chip row, and the hub panel (#1643).
      'All': 'Tous',
      'None': 'Aucun',
      'Clear the filters': 'Effacer les filtres',
      'Show only this hub': 'N\u2019afficher que ce pôle',
      'Shares members with': 'Membres en commun avec',
      'Close this panel': 'Fermer ce panneau',
      'Open the Working Group page': 'Ouvrir la page du groupe de travail',
      'Open in the Directory': 'Ouvrir dans l\u2019annuaire',
      'people in the network': 'personnes dans le réseau',
      'countries': 'pays',
      'research themes': 'thèmes de recherche',
      'ESSC co-panel ties': 'liens de panel ESSC',
      'co-authored outputs': 'publications co-signées',
      'with a directory profile': 'avec un profil dans l\'annuaire',
      '{n} members': '{n} membres',
      '{n} people work here': '{n} personnes y travaillent',
      'Shared an ESSC panel with {n} member': 'A partagé un panel ESSC avec {n} membre',
      'Shared an ESSC panel with {n} members': 'A partagé un panel ESSC avec {n} membres',
      'Co-authored with {n} member': 'A co-signé avec {n} membre',
      'Co-authored with {n} members': 'A co-signé avec {n} membres',
      'co-authored an Action output': 'a co-signé une publication de l\'Action',
      'The network map data could not be loaded.': 'Les données de la carte du réseau n\'ont pas pu être chargées.',
    },
    de: {
      'Action Chair': 'Aktionsvorsitz',
      'Action Vice-Chair': 'Stellv. Aktionsvorsitz',
      'Grant Holder Scientific Representative': 'Wissenschaftliche Vertretung des Förderträgers',
      'Science Communication Coordinator': 'Koordination Wissenschaftskommunikation',
      'Grant Awarding Coordinator': 'Koordination Fördervergabe',
      'Grant Awarding Coordinator Co-lead': 'Stellv. Koordination Fördervergabe',
      'WG1 Leader': 'Leitung WG1',
      'WG2 Leader': 'Leitung WG2',
      'WG3 Leader': 'Leitung WG3',
      'WG4 Leader': 'Leitung WG4',
      'WG1 Co-Leader': 'Co-Leitung WG1',
      'WG2 Co-Leader': 'Co-Leitung WG2',
      'WG3 Co-Leader': 'Co-Leitung WG3',
      'WG4 Co-Leader': 'Co-Leitung WG4',
      'Management Committee': 'Management-Ausschuss',
      'Event': 'Veranstaltung',
      'Publication': 'Publikation',
      'Announcement': 'Ankündigung',
      'Read more': 'Mehr lesen',
      'Read less': 'Weniger anzeigen',
      'Working Group participant': 'Arbeitsgruppen-Mitglied',
      'Bio coming soon.': 'Biografie folgt.',
      'View full profile': 'Vollständiges Profil ansehen',
      'View profile': 'Profil ansehen',
      'Quick look': 'Schnellansicht',
      'Member profile': 'Mitgliedsprofil',
      'Show more': 'Mehr anzeigen',
      'Show less': 'Weniger anzeigen',
      'member': 'Mitglied',
      'members': 'Mitglieder',
      'Show {0} members': '{0} Mitglieder anzeigen',
      'Remove filter': 'Filter entfernen',
      'Switch to dark mode': 'Dunkelmodus umschalten',
      'Switch to light mode': 'Hellmodus umschalten',
      'Unable to load network directory.': 'Netzwerkverzeichnis konnte nicht geladen werden.',
      'Please refresh, or use the {0}.': 'Bitte aktualisieren Sie die Seite oder nutzen Sie das {0}.',
      'contact page': 'Kontaktformular',
      'Research interests': 'Forschungsschwerpunkte',
      'Research themes': 'Forschungsthemen',
      'Research regions': 'Forschungsregionen',
      'Works on similar topics': 'Arbeitet zu ähnlichen Themen',
      'See everyone in these themes': 'Alle zu diesen Themen anzeigen',
      'Mentors on similar topics': 'Mentor·innen zu ähnlichen Themen',
      'See these mentors in the directory': 'Diese Mentor·innen im Verzeichnis ansehen',
      'In the EISS Anthology': 'In der EISS-Anthologie',
      'Show all': 'Alle anzeigen',
      'Show fewer': 'Weniger anzeigen',
      'Clear': 'Zurücksetzen',
      'Close': 'Schließen',
      'Filter by research interest': 'Nach Forschungsschwerpunkt filtern',
      'Directory last updated {0}.': 'Verzeichnis zuletzt aktualisiert am {0}.',
      'Available to mentor': 'Als Mentor verfügbar',
      'Seeking mentorship': 'Sucht Mentoring',
      'Mentoring, at capacity': 'Mentor, derzeit ausgelastet',
      'Recent publications': 'Neueste Veröffentlichungen',
      'Can host STSM visitors': 'Kann STSM-Gäste aufnehmen',
      'Open to hosting STSM visitors': 'Offen für STSM-Gäste (auf Anfrage)',
      'Mentorship matching': 'Mentoring-Vermittlung',
      'Mentoring in the network is informal. Introduce yourself directly and say what you are looking for. If you are unsure where to start, your Working Group lead can help make an introduction.': 'Mentoring im Netzwerk ist informell. Stellen Sie sich direkt vor und sagen Sie, was Sie suchen. Wenn Sie nicht wissen, wo Sie anfangen sollen, kann die Leitung Ihrer Arbeitsgruppe eine Verbindung herstellen.',
      'Offering mentorship': 'Bietet Mentoring',
      'No one here yet.': 'Noch niemand hier.',
      'No one in your selected research areas yet.': 'Noch niemand in Ihren ausgewählten Bereichen.',
      'Also show members offering mentorship': 'Auch Mitglieder anzeigen, die Mentoring anbieten',
      'Also show members seeking mentorship': 'Auch Mitglieder anzeigen, die Mentoring suchen',
      'In your selected research areas': 'In Ihren ausgewählten Bereichen',
      '{offer} offering mentoring, {seek} seeking a mentor': '{offer} bieten Mentoring an, {seek} suchen eine·n Mentor·in',
      'Shared research areas': 'Gemeinsame Forschungsbereiche',
      'Order for my career stage': 'Nach meiner Karrierestufe sortieren',
      // Warm contact intro (#1171). Twin of the FR block above; the build-time
      // copy lives in scripts/build-profile-pages.py (SCAFFOLDS). Edit both.
      'Introduce yourself by email': 'Per E-Mail vorstellen',
      'Mentorship enquiry via the NetSec directory': 'Mentoring-Anfrage über das NetSec-Verzeichnis',
      'Mentorship via the NetSec directory': 'Mentoring über das NetSec-Verzeichnis',
      'STSM hosting enquiry via the NetSec directory': 'STSM-Gastgeber-Anfrage über das NetSec-Verzeichnis',
      ' We share these research areas: {areas}.': ' Wir teilen diese Forschungsbereiche: {areas}.',
      ' I was drawn by your work on {areas}.': ' Ihre Arbeit zu {areas} hat mein Interesse geweckt.',
      "Dear {name},\n\nI found your profile in the NetSec directory.{areas_line}\n\nAbout me: [your name, career stage, institution, and a line on your research]\nWhat I am hoping for: [advice on publishing, a career conversation, feedback on a draft]\n\nWould you be open to a short online conversation in the coming weeks?\n\nBest regards,\n[your name]":
        "Guten Tag {name},\n\nich habe Ihr Profil im NetSec-Verzeichnis gefunden.{areas_line}\n\nZu mir: [Ihr Name, Karrierestufe, Institution und eine Zeile zu Ihrer Forschung]\nWas ich mir erhoffe: [Publikationsberatung, ein Karrieregespräch, Feedback zu einem Entwurf]\n\nWären Sie offen für ein kurzes Online-Gespräch in den kommenden Wochen?\n\nMit freundlichen Grüßen\n[Ihr Name]",
      "Dear {name},\n\nI saw in the NetSec directory that you are seeking mentorship.{areas_line}\n\nAbout me: [your name, role, institution, and the areas where you could help]\n\nIf useful, I would be happy to have a short conversation about your goals.\n\nBest regards,\n[your name]":
        "Guten Tag {name},\n\nich habe im NetSec-Verzeichnis gesehen, dass Sie Mentoring suchen.{areas_line}\n\nZu mir: [Ihr Name, Funktion, Institution und die Bereiche, in denen Sie helfen könnten]\n\nFalls hilfreich, würde ich mich über ein kurzes Gespräch über Ihre Ziele freuen.\n\nMit freundlichen Grüßen\n[Ihr Name]",
      "Dear {name},\n\nI found you in the NetSec directory as a possible STSM host.{areas_line}\n\nAbout me: [your name, career stage, institution]\nVisit idea: [topic and rough dates]\n\nAn STSM is a short funded research visit under the NetSec COST Action. If the fit looks right I would apply through e-COST. Would you be open to discussing it?\n\nBest regards,\n[your name]":
        "Guten Tag {name},\n\nich habe Sie im NetSec-Verzeichnis als möglichen STSM-Gastgeber gefunden.{areas_line}\n\nZu mir: [Ihr Name, Karrierestufe, Institution]\nIdee für den Besuch: [Thema und ungefähre Daten]\n\nEine STSM ist ein kurzer, von der COST Action NetSec finanzierter Forschungsaufenthalt. Wenn es passt, würde ich mich über e-COST bewerben. Wären Sie offen, darüber zu sprechen?\n\nMit freundlichen Grüßen\n[Ihr Name]",
      'Most relevant first': 'Relevanteste zuerst',
      'Any': 'Beliebig',
      'Doctoral': 'Promotion',
      'Early-career': 'Frühe Karriere',
      'Mid-career': 'Mittlere Karriere',
      'Senior': 'Erfahren',
      'Tip: add a research-theme or region filter above to narrow these lists to your own research area.': 'Tipp: Fügen Sie oben einen Themen- oder Regionsfilter hinzu, um diese Listen auf Ihren eigenen Bereich einzugrenzen.',
      'Show people outside your selected research areas': 'Personen außerhalb Ihrer ausgewählten Bereiche anzeigen',
      'Show only your selected research areas': 'Nur Ihre ausgewählten Bereiche anzeigen',
      // ── Mentorship wizard + grid (W5) ──
      // Per-locale sentence scaffold: German recasts the English participle
      // ("looking for") as a coordinated clause ("und suche") so verb-second
      // holds and the tokens sit naturally in the line.
      'I am': 'Ich bin',
      'looking for': 'und suche',
      'in': 'im Bereich',
      'a doctoral researcher': 'Doktorand·in',
      'an early-career researcher': 'Nachwuchswissenschaftler·in',
      'a mid-career researcher': 'Wissenschaftler·in mittlerer Laufbahn',
      'a senior researcher': 'erfahrene·r Wissenschaftler·in',
      'a mentor': 'eine·n Mentor·in',
      'a mentee': 'eine·n Mentee',
      'choose your stage': 'wählen Sie Ihre Stufe',
      'Career stage': 'Karrierestufe',
      'Looking for': 'Gesucht',
      'Research area': 'Themenfeld',
      'choose a research area': 'wählen Sie ein Themenfeld',
      '{n} offering': '{n} bieten an',
      '{n} seeking': '{n} suchen',
      'Guided': 'Geführt',
      'Browse all': 'Alle durchsuchen',
      'Mentorship view': 'Mentoring-Ansicht',
      'Matches update as you choose. Your stage and areas stay on this page only.': 'Die Treffer aktualisieren sich mit Ihrer Auswahl. Ihre Stufe und Ihre Bereiche bleiben nur auf dieser Seite.',
      'Mentoring in the network is informal: introduce yourself directly and say what you are looking for. Nothing you choose here is stored.': 'Mentoring im Netzwerk ist informell: Stellen Sie sich direkt vor und sagen Sie, was Sie suchen. Nichts, was Sie hier auswählen, wird gespeichert.',
      'Your closest matches': 'Ihre besten Treffer',
      'shared research areas first, then a mentor one or two steps ahead of you': 'zuerst gemeinsame Forschungsbereiche, dann ein·e Mentor·in ein bis zwei Schritte vor Ihnen',
      'shared research areas first, then someone a step or two earlier in their career': 'zuerst gemeinsame Forschungsbereiche, dann jemand ein bis zwei Schritte früher in der Laufbahn',
      'Best match': 'Bester Treffer',
      'No. 2': 'Nr. 2',
      'No. 3': 'Nr. 3',
      '{first} and {second}': '{first} und {second}',
      'Works on {areas}.': 'Arbeitet zu {areas}.',
      'Works on {areas} and is a near peer, recently in your shoes.': 'Arbeitet zu {areas} und ist auf einer ähnlichen Stufe, war kürzlich in Ihrer Lage.',
      'Works on {areas} and is one step ahead of you, the gap the mentoring literature favours.': 'Arbeitet zu {areas} und ist Ihnen einen Schritt voraus, der Abstand, den die Mentoring-Forschung bevorzugt.',
      'Works on {areas} and sits a couple of steps ahead of you.': 'Arbeitet zu {areas} und ist Ihnen ein paar Schritte voraus.',
      'Works on {areas} and is earlier in their career, someone you could support.': 'Arbeitet zu {areas} und steht früher in der Laufbahn, jemand, den Sie unterstützen könnten.',
      'Introduce yourself': 'Vorstellen',
      'Profile': 'Profil',
      'See all {n} offering mentorship': 'Alle {n} Mentoring-Angebote ansehen',
      'See all {n} seeking mentorship': 'Alle {n} Mentoring-Gesuche ansehen',
      '{n} people are seeking mentorship in your area, could you mentor one of them?': '{n} Personen suchen Mentoring in Ihrem Bereich. Könnten Sie eine davon begleiten?',
      '{n} people are offering mentorship in your area, could one of them help you?': '{n} Personen bieten Mentoring in Ihrem Bereich an. Könnte eine davon Ihnen helfen?',
      'Narrow the matches': 'Treffer eingrenzen',
      'Show people in:': 'Personen anzeigen in:',
      'All themes…': 'Alle Themen…',
      'Order for my stage:': 'Nach meiner Stufe ordnen:',
      'Offering mentorship in your area ({n})': 'Bieten Mentoring in Ihrem Bereich an ({n})',
      'Seeking mentorship in your area ({n})': 'Suchen Mentoring in Ihrem Bereich ({n})',
      'Offering mentorship ({n})': 'Bieten Mentoring an ({n})',
      'Seeking mentorship ({n})': 'Suchen Mentoring ({n})',
      'Most relevant first: shared research areas, then a mentor one or two steps ahead of you': 'Relevanteste zuerst: gemeinsame Forschungsbereiche, dann ein·e Mentor·in ein bis zwei Schritte vor Ihnen',
      'Most relevant first: shared research areas, then someone a step or two earlier in their career': 'Relevanteste zuerst: gemeinsame Forschungsbereiche, dann jemand ein bis zwei Schritte früher in der Laufbahn',
      'Show all {n} offering mentorship': 'Alle {n} Mentoring-Angebote anzeigen',
      'Show all {n} seeking mentorship': 'Alle {n} Mentoring-Gesuche anzeigen',
      'Near peer': 'Ähnliche Stufe',
      '1 step ahead': 'Einen Schritt voraus',
      '2 steps ahead': 'Zwei Schritte voraus',
      '{n} steps ahead': '{n} Schritte voraus',
      'Founding contributor': 'Gründungsbeteiligte:r',
      'Listed in the COST Open Call proposal OC-2024-1-27931': 'Im COST-Open-Call-Antrag OC-2024-1-27931 aufgeführt',
      'Research themes': 'Forschungsthemen',
      'Filter by research theme': 'Nach Forschungsthema filtern',
      'Foreign policy and diplomacy': 'Außenpolitik und Diplomatie',
      'Security and defence': 'Sicherheit und Verteidigung',
      'Strategy and deterrence': 'Strategie und Abschreckung',
      'European and transatlantic security order': 'Europäische und transatlantische Sicherheitsordnung',
      'Intelligence, information and influence': 'Nachrichtendienste, Information und Einflussnahme',
      'Identity, narratives and ideational security': 'Identität, Narrative und ideelle Sicherheit',
      'Cyber and emerging technology': 'Cyber und neue Technologien',
      'Economic security and geoeconomics': 'Wirtschaftssicherheit und Geoökonomie',
      'Transnational and human security': 'Transnationale und menschliche Sicherheit',
      'Peace, mediation and reconciliation': 'Frieden, Mediation und Versöhnung',
      'Theory and methods': 'Theorie und Methoden',
      'EU, UN and other international organisations': 'EU, UN und andere internationale Organisationen',
      'Crisis management and critical systems resilience': 'Krisenmanagement und Resilienz kritischer Systeme',
      'Political psychology, public opinion and decision-making': 'Politische Psychologie, öffentliche Meinung und Entscheidungsfindung',
      'Research regions': 'Forschungsregionen',
      'Filter by research region': 'Nach Forschungsregion filtern',
      'Europe': 'Europa',
      'Europe - Western Balkans': 'Europa - Westbalkan',
      'Europe - Eastern neighbours / Russia': 'Europa - Östliche Nachbarschaft / Russland',
      'Middle East and North Africa': 'Naher Osten und Nordafrika',
      'Africa': 'Afrika',
      'Asia': 'Asien',
      'The Americas': 'Amerika',
      'Global and cross-regional': 'Global und überregional',
      'Search': 'Suche',
      'Jump to the join form': 'Zum Formular springen',
      'Anyone can join': 'Beitritt offen für alle',
      'Filter by working group or Management Committee role': 'Nach Arbeitsgruppe oder Management-Ausschuss-Rolle filtern',
      'Filter by mentorship': 'Nach Mentoring filtern',
      'Filter by STSM hosting': 'Nach STSM-Gastgeberschaft filtern',
      'Filter by country': 'Nach Land filtern',
      'Switch card density': 'Kartendichte wechseln',
      'Filters': 'Filter',
      'Free-text search across names, affiliations, and countries. Combines with the filters.': 'Freitext-Suche über Namen, Affiliationen und Länder. Lässt sich mit den Filtern kombinieren.',
      'The + button takes you straight to the join card at the foot of this page.': 'Der +-Button bringt Sie direkt zur „Beitreten"-Karte am Seitenende.',
      'Add yourself via the form here. About three minutes to fill in. Cards appear on this page within a week of submission.': 'Tragen Sie sich über das Formular unten ein. Etwa drei Minuten. Die Karte erscheint binnen einer Woche nach Einreichung auf dieser Seite.',
      'WG1–WG4 filter by Working Group. The Management Committee chip surfaces only Management Committee representatives.': 'WG1–4 filtern nach Arbeitsgruppe. Die Pille „Management-Ausschuss" blendet nur Vertreter·innen des Management-Ausschusses ein.',
      'These chips group the directory by broad research theme, clustering people who work in the same area. Tap to narrow the list, tap more to widen the match. The keyword pills on each card are clickable too, and your selection lives in the URL so a filtered view is shareable.': 'Diese Pillen gruppieren das Verzeichnis nach grobem Forschungsthema und bündeln Personen, die im selben Bereich arbeiten. Klicken Sie, um die Liste einzugrenzen, klicken Sie weitere, um die Auswahl zu erweitern. Die Schlüsselwort-Pillen auf jeder Karte sind ebenfalls klickbar, und Ihre Auswahl steht in der URL, sodass sich eine gefilterte Ansicht teilen lässt.',
      'A second, geographic axis: the parts of the world members focus their research on, not where they are based. Combine it with the themes above to narrow by both.': 'Eine zweite, geografische Achse: die Weltregionen, auf die Mitglieder ihre Forschung richten, nicht wo sie ansässig sind. Kombinieren Sie sie mit den Themen oben, um nach beidem einzugrenzen.',
      'Members can flag that they are available to mentor early-career researchers, or seeking mentorship themselves. Use these chips to find them. This row appears once at least one member has opted in.': 'Mitglieder können angeben, dass sie als Mentor für Nachwuchsforschende verfügbar sind oder selbst Mentoring suchen. Mit diesen Chips finden Sie sie. Diese Reihe erscheint, sobald mindestens ein Mitglied teilnimmt.',
      'A Short-Term Scientific Mission is a funded research visit to another member’s institution. This chip surfaces the members who have offered to host STSM visitors.': 'Eine Short-Term Scientific Mission (STSM) ist ein finanzierter Forschungsaufenthalt an der Einrichtung eines anderen Mitglieds. Dieser Chip hebt die Mitglieder hervor, die angeboten haben, STSM-Gäste aufzunehmen.',
      'Detailed shows photos and bios. Compact shows initials, name, affiliation and Working-Group chips, three to a row. Your choice is remembered. Phones always use compact cards.': 'Die Detailansicht zeigt Fotos und Biografien. Die Kompaktansicht zeigt Initialen, Name, Affiliation und Arbeitsgruppen-Chips, drei pro Reihe. Ihre Wahl wird gespeichert. Telefone nutzen immer die Kompaktansicht.',
      'Tap Filters to narrow the directory by working group, research theme, research region, mentorship, or STSM hosting. The badge shows how many filters are active.': 'Tippen Sie auf „Filter", um das Verzeichnis nach Arbeitsgruppe, Forschungsthema, Forschungsregion, Mentoring oder STSM-Gastgeberschaft einzugrenzen. Das Abzeichen zeigt die Anzahl aktiver Filter.',
      'Next': 'Weiter',
      'Back': 'Zurück',
      'Done': 'Fertig',
      'Skip': 'Überspringen',
      'Step %1 of %2': 'Schritt %1 von %2',
      'Close tour': 'Tour schließen',
      // NetSec Network Map (#764), same set as the FR block above.
      'Working Groups': 'Arbeitsgruppen',
      'Building the Network': 'Aufbau des Netzwerks',
      'Transfer of Knowledge': 'Wissenstransfer',
      'Fostering the Next Generation of Scholars': 'Förderung der nächsten Generation von Forschenden',
      'Inclusion, Representativeness & Ethics': 'Inklusion, Repräsentativität und Ethik',
      'ESSC co-panels': 'Gemeinsame ESSC-Panels',
      'Edition': 'Ausgabe',
      'All editions': 'Alle Ausgaben',
      'Filter co-panels by conference edition': 'Gemeinsame Panels nach Konferenzausgabe filtern',
      'Mentorship offers & requests': 'Mentoring-Angebote und -Gesuche',
      'Co-authored outputs': 'Gemeinsame Veröffentlichungen',
      'showing all {n}': 'alle {n} angezeigt',
      'showing {n} of {m}': '{n} von {m} angezeigt',
      'Showing {n} of {m} people.': '{n} von {m} Personen angezeigt.',
      'No one on the map matches {q}.': 'Niemand auf der Karte entspricht {q}.',
      '{name} is on the map but hidden by the filters in use.': '{name} ist auf der Karte, wird aber von den aktiven Filtern ausgeblendet.',
      'Showing {name}.': '{name} wird hervorgehoben.',
      'That link filtered the map to hubs it does not hold, so the whole map is shown.': 'Dieser Link filterte die Karte auf Knotenpunkte, die sie nicht enthält, daher wird die ganze Karte angezeigt.',
      'See this member on the Network Map': 'Dieses Mitglied auf der Netzwerkkarte ansehen',
      'All': 'Alle',
      'None': 'Keine',
      'Clear the filters': 'Filter zurücksetzen',
      'Show only this hub': 'Nur diesen Knotenpunkt zeigen',
      'Shares members with': 'Gemeinsame Mitglieder mit',
      'Close this panel': 'Dieses Panel schließen',
      'Open the Working Group page': 'Die Arbeitsgruppenseite öffnen',
      'Open in the Directory': 'Im Verzeichnis öffnen',
      'people in the network': 'Personen im Netzwerk',
      'countries': 'Länder',
      'research themes': 'Forschungsthemen',
      'ESSC co-panel ties': 'ESSC-Panel-Verbindungen',
      'co-authored outputs': 'gemeinsame Veröffentlichungen',
      'with a directory profile': 'mit Profil im Verzeichnis',
      '{n} members': '{n} Mitglieder',
      '{n} people work here': '{n} Personen arbeiten hier',
      'Shared an ESSC panel with {n} member': 'Teilte ein ESSC-Panel mit {n} Mitglied',
      'Shared an ESSC panel with {n} members': 'Teilte ein ESSC-Panel mit {n} Mitgliedern',
      'Co-authored with {n} member': 'Gemeinsame Veröffentlichung mit {n} Mitglied',
      'Co-authored with {n} members': 'Gemeinsame Veröffentlichung mit {n} Mitgliedern',
      'co-authored an Action output': 'hat eine Veröffentlichung der Aktion mitverfasst',
      'The network map data could not be loaded.': 'Die Daten der Netzwerkkarte konnten nicht geladen werden.',
    },
  };
  /* Country-name table for the " · <Country>" tail of role strings like
     "Management Committee · Switzerland" (data/mc-members.json / bios.json
     always carry the English exonym). Covers every country appearing in
     either data file. */
  const COUNTRY_I18N = {
    fr: {
      'Albania': 'Albanie', 'Austria': 'Autriche', 'Belgium': 'Belgique',
      'Bosnia and Herzegovina': 'Bosnie-Herzégovine', 'Bulgaria': 'Bulgarie',
      'Canada': 'Canada', 'Croatia': 'Croatie', 'Cyprus': 'Chypre',
      'Czechia': 'Tchéquie', 'Denmark': 'Danemark', 'Finland': 'Finlande',
      'France': 'France', 'Georgia': 'Géorgie', 'Germany': 'Allemagne',
      'Greece': 'Grèce', 'Iceland': 'Islande', 'Ireland': 'Irlande',
      'Italy': 'Italie', 'Lithuania': 'Lituanie', 'Moldova': 'Moldavie',
      'Montenegro': 'Monténégro', 'Netherlands': 'Pays-Bas',
      'North Macedonia': 'Macédoine du Nord', 'Norway': 'Norvège',
      'Poland': 'Pologne', 'Portugal': 'Portugal', 'Romania': 'Roumanie',
      'Serbia': 'Serbie', 'Slovakia': 'Slovaquie', 'Slovenia': 'Slovénie',
      'Spain': 'Espagne', 'Sweden': 'Suède', 'Switzerland': 'Suisse',
      'Türkiye': 'Turquie', 'Ukraine': 'Ukraine',
      'United Kingdom': 'Royaume-Uni', 'United States': 'États-Unis',
    },
    de: {
      'Albania': 'Albanien', 'Austria': 'Österreich', 'Belgium': 'Belgien',
      'Bosnia and Herzegovina': 'Bosnien und Herzegowina', 'Bulgaria': 'Bulgarien',
      'Canada': 'Kanada', 'Croatia': 'Kroatien', 'Cyprus': 'Zypern',
      'Czechia': 'Tschechien', 'Denmark': 'Dänemark', 'Finland': 'Finnland',
      'France': 'Frankreich', 'Georgia': 'Georgien', 'Germany': 'Deutschland',
      'Greece': 'Griechenland', 'Iceland': 'Island', 'Ireland': 'Irland',
      'Italy': 'Italien', 'Lithuania': 'Litauen', 'Moldova': 'Moldau',
      'Montenegro': 'Montenegro', 'Netherlands': 'Niederlande',
      'North Macedonia': 'Nordmazedonien', 'Norway': 'Norwegen',
      'Poland': 'Polen', 'Portugal': 'Portugal', 'Romania': 'Rumänien',
      'Serbia': 'Serbien', 'Slovakia': 'Slowakei', 'Slovenia': 'Slowenien',
      'Spain': 'Spanien', 'Sweden': 'Schweden', 'Switzerland': 'Schweiz',
      'Türkiye': 'Türkei', 'Ukraine': 'Ukraine',
      'United Kingdom': 'Vereinigtes Königreich', 'United States': 'Vereinigte Staaten',
    },
  };
  /** Translate a known string for the current page's language.
   *  Falls back to the original if no translation is registered.
   *  Strings of the form "Management Committee · Switzerland" translate
   *  both the prefix before " · " (via I18N) and the country name after it
   *  (via COUNTRY_I18N), independently, so an unrecognised role prefix or
   *  country still falls back to its English original. */
  window.netsecT = function (s) {
    if (typeof s !== 'string') return s;
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const dict = I18N[lang];
    if (!dict) return s;
    const sep = ' · ';
    if (s.includes(sep)) {
      const [head, ...rest] = s.split(sep);
      const tail = rest.join(sep);
      const countries = COUNTRY_I18N[lang];
      return (dict[head] || head) + sep + ((countries && countries[tail]) || tail);
    }
    return dict[s] || s;
  };

  /* Country-name translator. COUNTRY_I18N is module-scoped, so page
     scripts (the directory flag strip, for one) reach a translated
     country name through this accessor rather than the ' · ' composite
     trick netsecT uses internally. Falls back to the English name when
     the locale carries no entry. */
  window.netsecCountry = function (name) {
    if (typeof name !== 'string') return name;
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const countries = COUNTRY_I18N[lang];
    return (countries && countries[name]) || name;
  };

  /* Headshot WebP helper (#269). The directory cards, the ESSC member
     popover, and the About / Working-Group avatars all serve
     <picture><source type="image/webp"><img original></picture>, so a
     modern browser fetches the ~50%-smaller WebP and the original JPEG /
     PNG stays as the fallback. sync-bios.py writes a `<slug>.webp`
     sibling for every headshot. Returns the WebP path, or null when the
     source is absent or already WebP (nothing to add). */
  window.netsecWebp = function (path) {
    if (typeof path !== 'string') return null;
    return /\.(jpe?g|png)$/i.test(path)
      ? path.replace(/\.(jpe?g|png)$/i, '.webp')
      : null;
  };

  /* Two-letter avatar initials: strip the salutation, take the first
     letter of the first and last name. Single sitewide rule (#1194).
     Four forked copies had drifted (the directory took the first two
     words instead of first and last). Plain text: callers that build
     HTML strings escape it themselves. */
  window.netsecInitials = function (name) {
    const tokens = String(name || '')
      .replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '')
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (tokens.length === 0) return '?';
    const first = tokens[0].charAt(0);
    const last = tokens.length > 1 ? tokens[tokens.length - 1].charAt(0) : '';
    return (first + last).toUpperCase() || '?';
  };

  /* Title-case a research keyword or theme for chip text, preserving
     acronyms and internal capitals, lowercasing small connector words
     after the first. Shared by the directory and the home spotlight
     so both render identical chip labels (#1194). */
  const TITLE_SMALL = new Set(['a', 'an', 'and', 'the', 'of', 'for', 'in', 'on', 'to', 'with', 'vs']);
  window.netsecTitlecaseTheme = function (raw) {
    return String(raw || '').split(/\s+/).map((w, i) => {
      if (!w) return w;
      if (w === w.toUpperCase() && /[A-Z]/.test(w)) return w;   // acronym
      if (/[A-Z]/.test(w.slice(1))) return w;                    // internal cap
      const lw = w.toLowerCase();
      if (i !== 0 && TITLE_SMALL.has(lw)) return lw;
      return lw.charAt(0).toUpperCase() + lw.slice(1);
    }).join(' ');
  };

  /* Beta-translation ribbon: keep the layout offset in step with the
     ribbon's real measured height.

     The ribbon is `position: fixed; top: 0` and the body's
     `padding-top` + nav's `top` are derived from `--ribbon-h` so
     content doesn't sit under it. The fallback in CSS is 38px
     (single-line desktop). On narrow viewports the long
     "Traduction automatique…" sentence + link wraps to two or
     three lines, making the ribbon 60–100px tall. Without this
     measurement the nav would overlap the bottom of the ribbon
     (reported on mobile).

     The measurement runs:
       - once on script start (catches the initial layout),
       - on every viewport resize (catches wrap-state changes),
       - on every ribbon resize (covers anything we don't predict).
  */
  const ribbon = document.querySelector('.i18n-beta-ribbon');
  if (ribbon && document.documentElement.hasAttribute('data-i18n-status')) {
    const syncRibbonHeight = () => {
      const h = ribbon.offsetHeight;
      if (h > 0) {
        document.documentElement.style.setProperty('--ribbon-h', h + 'px');
      }
    };
    // Run now (best-effort: defer scripts run after DOM but before
    // CSS is guaranteed to have applied, so offsetHeight may still be
    // 0 here), then again once everything has loaded, then on every
    // viewport resize / ribbon resize. The window.load + ResizeObserver
    // pair guarantees we eventually set the right value even if the
    // synchronous read returned 0.
    syncRibbonHeight();
    if (document.readyState !== 'complete') {
      window.addEventListener('load', syncRibbonHeight, { once: true });
    }
    window.addEventListener('resize', syncRibbonHeight, { passive: true });
    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(syncRibbonHeight).observe(ribbon);
    }
  }

  /* Nav: stronger shadow once scrolled past the top. */
  const nav = document.querySelector('.nav');
  if (nav) {
    const onScroll = () => {
      nav.style.boxShadow = window.scrollY > 12
        ? '0 14px 40px rgba(20,35,80,.14)'
        : 'var(--glass-shadow)';
    };
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* Anchor-scroll offset + precise in-page section navigation.

     Two problems this solves:
       1. The header is `position: fixed` and its height varies with
          the beta ribbon and the What's-New banner, so the static
          `scroll-padding-top` in CSS lands section headings under it.
          We measure the real header bottom and publish it as
          scroll-padding-top, recomputed whenever the ribbon, banner,
          or nav changes size. This governs native hash landings
          (page load with a #hash, and cross-page links like
          working-groups.html#wg1).
       2. The primary nav links are authored as `index.html#section`
          so they resolve from every page. On the home page itself
          that points at the same document but with a different path
          string, so the browser does a full reload + native hash jump
          rather than an in-page scroll, and the events / spotlight
          blocks that render in after load throw the landing off.
          We intercept header- and jump-nav links that resolve to the
          current document and scroll to them ourselves, clearing the
          measured header. */
  (function () {
    const headerBottom = () =>
      nav ? Math.max(0, nav.getBoundingClientRect().bottom) : 78;
    const syncPad = () => {
      document.documentElement.style.scrollPaddingTop =
        Math.round(headerBottom() + 14) + 'px';
    };
    syncPad();
    window.addEventListener('load', syncPad);
    window.addEventListener('resize', syncPad, { passive: true });
    if (nav && typeof ResizeObserver === 'function') {
      new ResizeObserver(syncPad).observe(nav);
      const rib = document.querySelector('.i18n-beta-ribbon');
      if (rib) new ResizeObserver(syncPad).observe(rib);
    }
    // The nav is `position: fixed` and its `top` is driven by the CSS
    // vars --whats-new-h / --ribbon-h, which the banner and ribbon set
    // on <html> *after* this runs. Changing top moves the nav without
    // resizing it, so the ResizeObserver above never fires. Watch the
    // <html> style attribute (where those vars live) and recompute, and
    // re-measure a few times early on to catch the async banner mount.
    if (typeof MutationObserver === 'function') {
      new MutationObserver(syncPad).observe(document.documentElement,
        { attributes: true, attributeFilter: ['style'] });
    }
    [150, 500, 1200].forEach((d) => setTimeout(syncPad, d));

    // Normalise so "/", "/index.html", "/index.fr.html" compare equal.
    const normPath = (p) =>
      p.replace(/index(\.[a-z]{2})?\.html$/, '').replace(/\/+$/, '') || '/';
    const inPageTarget = (a) => {
      if (!a || !a.hash || a.host !== location.host) return null;
      if (normPath(a.pathname) !== normPath(location.pathname)) return null;
      let id;
      try { id = decodeURIComponent(a.hash.slice(1)); } catch (_) { return null; }
      return id ? document.getElementById(id) : null;
    };
    document.addEventListener('click', (e) => {
      const a = e.target.closest && e.target.closest(
        '.nav-links a[href], .wg-jump a[href]');
      if (!a) return;
      const target = inPageTarget(a);
      if (!target) return;             // cross-page or no such section: let it navigate
      e.preventDefault();
      const y = window.scrollY + target.getBoundingClientRect().top
        - headerBottom() - 14;
      const reduce = window.matchMedia
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: Math.max(0, y), behavior: reduce ? 'auto' : 'smooth' });
      if (history.replaceState) history.replaceState(null, '', a.hash);
      // Move focus to the section for keyboard / screen-reader users,
      // without letting .focus() yank the scroll position back.
      target.setAttribute('tabindex', '-1');
      try { target.focus({ preventScroll: true }); } catch (_) {}
    });
  })();

  /* Theme toggle — flips .dark on <html>, persists choice.
     Initial state is set by the inline <head> script to avoid FOUC. */
  const themeBtn = document.querySelector('.theme-toggle');
  if (themeBtn) {
    // aria-label and title are kept in step with the current theme.
    // The strings flow through window.netsecT() so the FR/DE pages
    // get translated labels for screen-reader users.
    const setLabel = () => {
      const dark = document.documentElement.classList.contains('dark');
      const key = dark ? 'Switch to light mode' : 'Switch to dark mode';
      const t = (window.netsecT && window.netsecT(key)) || key;
      themeBtn.setAttribute('aria-label', t);
      themeBtn.setAttribute('title', t);
    };
    setLabel();
    themeBtn.addEventListener('click', () => {
      const nowDark = document.documentElement.classList.toggle('dark');
      try { localStorage.setItem('netsec-theme', nowDark ? 'dark' : 'light'); } catch (e) {}
      setLabel();
    });
  }

  /* MC-by-country collapsible: persist open/closed state, auto-open
     on deep-link to a country card inside. */
  const mcDetails = document.getElementById('mc-countries');
  if (mcDetails) {
    try {
      if (localStorage.getItem('netsec-mc-countries-open') === '1') mcDetails.open = true;
    } catch (e) {}
    try {
      if (location.hash && location.hash.length > 1) {
        const target = document.querySelector(location.hash);
        if (target && mcDetails.contains(target)) mcDetails.open = true;
      }
    } catch (e) {}
    mcDetails.addEventListener('toggle', () => {
      try { localStorage.setItem('netsec-mc-countries-open', mcDetails.open ? '1' : '0'); } catch (e) {}
    });
  }

  /* Language switcher (Phase 2)
     ────────────────────────────────────────────────────────────────
     Three responsibilities:
       1) Rewrite the switcher chip hrefs to point at the same page in
          each language. Each chip carries hreflang; the JS swaps the
          suffix to land on the matching locale variant. This means
          every page can ship an identical chip block and the JS
          figures out the destinations.
       2) Mark the chip whose hreflang matches <html lang> with
          aria-current="true" so screen readers and the active-style
          rule (white pill background) light up the right one.
       3) On click, save the preference to localStorage. On every
          subsequent page load, if the user is on the English version
          but the preference is FR or DE, redirect them — *only* when
          an <link rel="alternate" hreflang="…"> is declared for the
          current page (no 404 redirects). */
  (function langSwitcher() {
    const currentLang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);

    // --- (1) and (2): rewire chip hrefs + aria-current
    const chips = document.querySelectorAll('.lang-switch a');
    if (chips.length) {
      // Compute the canonical English filename of the page we're on.
      // Strip the trailing /, normalise index, drop the .fr/.de locale
      // suffix if present.
      let here = location.pathname.replace(/\/$/, '/index.html').split('/').pop();
      if (!here) here = 'index.html';
      const stem = here.replace(/\.(fr|de)\.html$/i, '.html');
      const variants = {
        en: stem,
        fr: stem.replace(/\.html$/, '.fr.html'),
        de: stem.replace(/\.html$/, '.de.html'),
      };
      chips.forEach(a => {
        const lang = (a.getAttribute('hreflang') || '').toLowerCase();
        if (lang && variants[lang]) {
          // Preserve any hash on the current page so deep-links survive.
          a.href = variants[lang] + (location.hash || '');
        }
        a.setAttribute('aria-current', lang === currentLang ? 'true' : 'false');
        // Persist the preference on click.
        a.addEventListener('click', () => {
          try { localStorage.setItem('netsec-lang', lang); } catch (e) {}
        });
      });
    }

    // Beta-translation ribbon: the "View in English" link inside
    // `.i18n-beta-ribbon` lives outside `.lang-switch`, so without this
    // it doesn't update `netsec-lang`. Result: the auto-redirect below
    // bounces the user from EN straight back to the FR / DE page they
    // just left. Persist the destination language on click so the
    // ribbon-driven switch sticks (#253).
    document.querySelectorAll('.i18n-beta-ribbon a[hreflang]').forEach(a => {
      a.addEventListener('click', () => {
        try {
          const lang = (a.getAttribute('hreflang') || '').toLowerCase();
          if (lang) localStorage.setItem('netsec-lang', lang);
        } catch (e) {}
      });
    });

    // --- (3): redirect to saved preference when safe
    try {
      const saved = localStorage.getItem('netsec-lang');
      if (!saved || saved === currentLang) return;
      const alt = document.querySelector('link[rel="alternate"][hreflang="' + saved + '"]');
      if (!alt || !alt.href) return;
      // Avoid loops: only redirect if we're actually on a different URL.
      const here = location.origin + location.pathname;
      const there = alt.href.split('#')[0];
      if (here === there) return;
      // Only auto-redirect from the authoritative English to a saved
      // FR/DE — never the other direction. This keeps the English
      // version reachable as a fallback when a translation is broken.
      if (currentLang !== 'en') return;
      location.replace(alt.href + (location.hash || ''));
    } catch (e) { /* localStorage / DOM API may be unavailable */ }
  })();

  /* Mobile menu */
  const menuBtn = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open);
    });
    navLinks.addEventListener('click', e => {
      if (e.target.tagName === 'A') navLinks.classList.remove('open');
    });
  }

  /* Reveal-on-scroll. threshold:0 + bottom rootMargin so very tall
     sections (eg. Management Committee) still trigger reliably on
     phones — see commit history for the diagnosis. */
  try {
    const targets = document.querySelectorAll('.reveal');
    if (targets.length) {
      document.documentElement.classList.add('js-reveal');
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { threshold: 0, rootMargin: '0px 0px -10% 0px' });
      targets.forEach(el => io.observe(el));
      // Safety: never leave anything stuck at opacity:0
      setTimeout(() => targets.forEach(el => el.classList.add('in')), 3000);
    }
  } catch (err) {
    document.documentElement.classList.remove('js-reveal');
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }

  /* Year stamp in the footer */
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ─────────────────────────────────────────────────────────────
     Live-refresh leadership cards from data/bios.json.
     ─────────────────────────────────────────────────────────────
     The home page leadership cards (Action Leadership, WG Leadership,
     WG Co-Leaders) are hand-authored HTML — they need to render even
     before any JS runs, since they sit above the fold and appear in
     view-source. But once a leader submits a refreshed photo or
     affiliation via the public Google Form, the new data lives in
     data/bios.json while the hand-authored HTML still points at the
     old photo file. This block reconciles the two on page load.

     Contract:
       - Card opts in by carrying data-slug="…" matching its bios.json id,
         or, when no slug is present, by its name matching a directory
         entry (same first|last matcher the ESSC programme and Summer
         School roster use). The slug wins when both could resolve.
       - Photo + heading are always refreshed when the slug resolves.
       - The .org line is only refreshed when the card carries
         data-org-from-bio="affiliation" (currently the five Co-Leader
         cards). Other cards keep their hand-authored .org text because
         it is not an affiliation — it is "WG1 Leader", "Outreach &
         dissemination", "Co-lead: <Name>", etc.
       - On any error (no JS, fetch fails, slug absent), the static
         HTML stays exactly as written. Nothing is hidden, nothing is
         blanked. */
  // First|last name key for the no-slug fallback below. Drops titles and
  // nobiliary particles, folds diacritics, strips apostrophes, the same
  // scheme the ESSC programme and Summer School roster use. Kept local so
  // this block stays self-contained.
  const LEADER_POSTNOMINALS = new Set(['phd', 'jr', 'sr', 'ii', 'iii', 'iv', 'esq']);
  const LEADER_PARTICLES = new Set([
    'de', 'del', 'della', 'di', 'da', 'das', 'dos',
    'van', 'von', 'vom', 'der', 'den', 'ter', 'ten',
    'la', 'le', 'el', 'al', 'ibn', 'bin', 'bint', 'zu', 'auf', 'af',
  ]);
  function leaderNameKey(name) {
    if (!name) return null;
    let s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '');
    s = s.replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '').replace(/[‘’ʼ'`]/g, '');
    const t = s.split(/[^A-Za-z]+/).filter(Boolean).map(x => x.toLowerCase())
      .filter(x => !LEADER_POSTNOMINALS.has(x) && !LEADER_PARTICLES.has(x));
    if (t.length < 2) return null;
    return t[0] + '|' + t[t.length - 1];
  }
  // Cards may carry data-slug, data-person (the authored name), or both.
  // Selecting on either lets a card resolve by name even without a slug.
  const leaderCards = document.querySelectorAll('.mc-card[data-slug], .mc-card[data-person]');
  if (leaderCards.length) {
    (async () => {
      try {
        const res = await fetch('data/bios.json', { cache: 'no-cache' });
        if (!res.ok) return;
        const data = await res.json();
        const bySlug = Object.create(null);
        const byName = new Map();
        (data.members || []).forEach(m => {
          if (m.id) bySlug[m.id] = m;
          const add = (nm) => { const k = leaderNameKey(nm); if (k && !byName.has(k)) byName.set(k, m); };
          add(m.name);
          (m.name_aliases || []).forEach(add);
        });

        leaderCards.forEach(card => {
          const slug = card.getAttribute('data-slug');
          let m = slug ? bySlug[slug] : null;
          if (!m) {
            // No slug, or a slug that no longer resolves: fall back to the
            // card's name. A new leader is reconciled without anyone
            // hand-writing a data-slug, and the card self-heals as the
            // directory fills in.
            const nm = card.getAttribute('data-person') || ((card.querySelector('h4') || {}).textContent);
            m = byName.get(leaderNameKey(nm));
          }
          if (!m) return;

          // Photo
          if (m.photo) {
            const img = card.querySelector('.mc-avatar img');
            if (img) {
              if (img.getAttribute('src') !== m.photo) img.setAttribute('src', m.photo);
              if (m.name) img.setAttribute('alt', m.name);
              // Wrap the avatar in <picture> with a WebP source (#269);
              // the original <img> stays as the fallback. Idempotent.
              const webp = window.netsecWebp && window.netsecWebp(m.photo);
              if (webp) {
                let pic = img.closest('picture');
                if (!pic) {
                  pic = document.createElement('picture');
                  const src = document.createElement('source');
                  src.type = 'image/webp';
                  src.srcset = webp;
                  img.parentNode.insertBefore(pic, img);
                  pic.appendChild(src);
                  pic.appendChild(img);
                } else {
                  const src = pic.querySelector('source');
                  if (src) src.srcset = webp;
                }
              }
            }
          }
          // Display name (honorifics sometimes change between
          // initial seed and a refreshed form submission)
          if (m.name) {
            const h = card.querySelector('h4');
            if (h && h.textContent.trim() !== m.name) h.textContent = m.name;
          }
          // Affiliation line, opt-in
          if (card.getAttribute('data-org-from-bio') === 'affiliation') {
            const org = card.querySelector('.org');
            if (org && m.affiliation && org.textContent.trim() !== m.affiliation) {
              org.textContent = m.affiliation;
            }
          }
        });
      } catch (err) {
        // Silent: the static HTML is already a correct fallback.
      }
    })();
  }

  /* ─────────────────────────────────────────────────────────────
     Guided tour engine — netsecTour({steps, labels, onComplete})
     ─────────────────────────────────────────────────────────────
     Coachmark-style walkthrough exposed as window.netsecTour so
     page-specific scripts can configure their own tours. Currently
     used by /people/ for the directory orientation; designed to be
     reusable on other pages later.

     Each `step` is { target, title, body, scroll? }:
       - target : CSS selector for the element to spotlight.
       - title  : short heading shown above the body.
       - body   : one or two short sentences.
       - scroll : optional bool. If true, the target is scrolled
                  into view before the spotlight is positioned —
                  needed for the "Join CTA" step which sits below
                  the fold on most viewports.

     `labels` carries the localised UI strings: next / prev / done
     / skip / stepOf (e.g. "Step 2 of 5"). Tour module never
     synthesises strings; everything visible comes from labels.

     `onComplete` fires when the user finishes or skips — used by
     the caller to set localStorage so the first-visit welcome
     strip stays dismissed.

     Behaviour:
       - Backdrop dims the page (50% black). Spotlight is a glowing
         ring around the target. Tooltip card carries the step
         content + Prev / Next / Done buttons.
       - Tooltip positions itself below the target by default, or
         above when the target sits in the bottom half of the
         viewport. On narrow viewports (< 640 px) it spans the
         full width minus a 12 px margin.
       - Focus trap: Tab cycles only inside the tooltip's buttons.
       - Keyboard: Enter advances (matching the focused Next
         button), Esc exits (treated as a skip), Left/Right arrows
         step back/forward.
       - prefers-reduced-motion: animations are disabled (the
         transitions are pure CSS so this is handled in the stylesheet).
       - On viewport resize, the spotlight + tooltip reposition.
       - If a target selector resolves to nothing (e.g. the page
         changed shape), that step is skipped silently and the tour
         continues. */
  function netsecTour(config) {
    const steps  = (config && config.steps) || [];
    const labels = Object.assign(
      { next: 'Next', prev: 'Back', done: 'Done', skip: 'Skip',
        stepOf: 'Step %1 of %2', closeLabel: 'Close tour' },
      (config && config.labels) || {}
    );
    const onComplete = (config && config.onComplete) || function () {};

    let idx = -1;
    let backdrop = null, spotlight = null, tooltip = null;
    let prevFocus = null;
    let resizeBound = null;

    function $el(tag, cls, html) {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      if (html !== undefined) el.innerHTML = html;
      return el;
    }

    function mount() {
      backdrop  = $el('div', 'tour-backdrop');
      spotlight = $el('div', 'tour-spotlight');
      tooltip   = $el('div', 'tour-tooltip', '');
      tooltip.setAttribute('role', 'dialog');
      tooltip.setAttribute('aria-modal', 'true');
      tooltip.setAttribute('aria-live', 'polite');
      document.body.appendChild(backdrop);
      document.body.appendChild(spotlight);
      document.body.appendChild(tooltip);
      // Click outside the tooltip (i.e. on the backdrop) is a skip.
      backdrop.addEventListener('click', skip);
    }

    function unmount() {
      [backdrop, spotlight, tooltip].forEach(n => n && n.remove());
      backdrop = spotlight = tooltip = null;
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', resizeBound);
      window.removeEventListener('scroll', resizeBound, true);
      if (prevFocus && typeof prevFocus.focus === 'function') {
        try { prevFocus.focus(); } catch (e) {}
      }
    }

    function start() {
      if (!steps.length) return;
      prevFocus = document.activeElement;
      mount();
      resizeBound = () => positionForStep(steps[idx]);
      window.addEventListener('resize', resizeBound);
      // Use capture so we catch any container's scroll, not only window's.
      window.addEventListener('scroll', resizeBound, true);
      document.addEventListener('keydown', onKey);
      idx = 0;
      render();
    }

    function next() {
      if (idx >= steps.length - 1) return done();
      idx++;
      render();
    }
    function prev() {
      if (idx <= 0) return;
      idx--;
      render();
    }
    function done() { unmount(); onComplete('done'); }
    function skip() { unmount(); onComplete('skip'); }

    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); return skip(); }
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault(); return next();
      }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault(); return prev();
      }
      // Focus trap: keep Tab inside the tooltip's buttons.
      if (e.key === 'Tab' && tooltip) {
        const focusables = tooltip.querySelectorAll('button');
        if (!focusables.length) return;
        const first = focusables[0];
        const last  = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault(); last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault(); first.focus();
        }
      }
    }

    // True when the element sits comfortably within the viewport, below
    // the fixed nav and above the fold, so the tour need not scroll to it.
    function isTargetInView(el) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return false;
      const nav = document.querySelector('.nav');
      const navBottom = nav ? Math.max(0, nav.getBoundingClientRect().bottom) : 0;
      return r.top >= navBottom + 8 && r.bottom <= window.innerHeight - 8;
    }

    function render() {
      const step = steps[idx];
      if (!step) return done();
      const target = document.querySelector(step.target);
      if (!target || target.hidden) {
        // Target missing, or present but hidden (e.g. a data-driven
        // filter row that has no data yet, like the keyword or
        // mentorship filters) — silently advance to keep the tour going.
        if (idx < steps.length - 1) return next();
        return done();
      }
      // If the target sits inside a collapsed disclosure (the "More
      // filters" panel now holds the theme + mentorship facets), open it
      // so the step has a real, measurable rectangle.
      const host = target.closest('details');
      if (host && !host.open) host.open = true;
      // The tour can be launched from any scroll position — the "?" lives
      // in a pinned tools bar — so always bring the target into view before
      // positioning. A step whose target is off-screen would otherwise
      // anchor its spotlight and tooltip to an off-screen rectangle.
      if (isTargetInView(target)) {
        positionForStep(step);
      } else {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Wait briefly for the smooth scroll to settle before positioning.
        setTimeout(() => positionForStep(step), 360);
      }
      // Render the tooltip content. Buttons in DOM order: Prev → Skip → Next/Done.
      const showPrev = idx > 0;
      const isLast   = idx === steps.length - 1;
      const stepLabel = labels.stepOf
        .replace('%1', String(idx + 1)).replace('%2', String(steps.length));
      tooltip.innerHTML = '';
      const titleEl   = $el('h3', 'tour-title');
      titleEl.textContent = step.title || '';
      const bodyEl    = $el('p',  'tour-body');
      bodyEl.textContent = step.body || '';
      const footerEl  = $el('div', 'tour-footer');
      const progress  = $el('span', 'tour-progress');
      progress.textContent = stepLabel;
      const actions   = $el('div', 'tour-actions');
      if (showPrev) {
        const b = $el('button', 'tour-btn tour-btn-ghost');
        b.type = 'button'; b.textContent = labels.prev;
        b.addEventListener('click', prev);
        actions.appendChild(b);
      }
      const skipBtn = $el('button', 'tour-btn tour-btn-ghost');
      skipBtn.type = 'button'; skipBtn.textContent = labels.skip;
      skipBtn.addEventListener('click', skip);
      actions.appendChild(skipBtn);
      const nextBtn = $el('button', 'tour-btn tour-btn-primary');
      nextBtn.type = 'button';
      nextBtn.textContent = isLast ? labels.done : labels.next;
      nextBtn.addEventListener('click', isLast ? done : next);
      actions.appendChild(nextBtn);
      footerEl.appendChild(progress);
      footerEl.appendChild(actions);
      tooltip.appendChild(titleEl);
      tooltip.appendChild(bodyEl);
      tooltip.appendChild(footerEl);
      // Focus the Next/Done button so Enter advances.
      requestAnimationFrame(() => nextBtn.focus());
      // Reveal the backdrop on the first render (it mounts hidden).
      backdrop.classList.add('is-visible');
    }

    function positionForStep(step) {
      if (!step || !tooltip || !spotlight) return;
      const target = document.querySelector(step.target);
      if (!target) return;
      const rect = target.getBoundingClientRect();
      // Spotlight is positioned in the viewport (fixed). We pad the
      // target rectangle by 6 px so the ring sits just outside it.
      const pad = 6;
      spotlight.style.top    = (rect.top - pad) + 'px';
      spotlight.style.left   = (rect.left - pad) + 'px';
      spotlight.style.width  = (rect.width + pad * 2) + 'px';
      spotlight.style.height = (rect.height + pad * 2) + 'px';

      // Tooltip placement. Prefer below; flip to above if the
      // target's bottom is in the lower half of the viewport.
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const ttRect = tooltip.getBoundingClientRect();
      // We need to set position first, then measure — but the
      // tooltip may not have a stable size yet. Use a sensible
      // estimate (180px tall) for the first frame, then refine.
      const ttH = ttRect.height || 180;
      const ttW = Math.min(360, vw - 24);
      tooltip.style.width = ttW + 'px';
      const gap = 14;
      const placeBelow = (rect.bottom + ttH + gap) < vh - 8;
      let top  = placeBelow ? (rect.bottom + gap) : (rect.top - ttH - gap);
      // Clamp into viewport vertically.
      top = Math.max(8, Math.min(top, vh - ttH - 8));
      // Horizontally: try to centre on the target, then clamp.
      let left = rect.left + (rect.width / 2) - (ttW / 2);
      left = Math.max(12, Math.min(left, vw - ttW - 12));
      tooltip.style.top  = top + 'px';
      tooltip.style.left = left + 'px';
    }

    return { start };
  }
  window.netsecTour = netsecTour;
})();

/* ════════════════════════════════════════════════════════════════
   SITE-WIDE SEARCH (Pagefind)
   ────────────────────────────────────────────────────────────────
   A modal overlay search UI powered by a Pagefind index served from
   /pagefind/. Triggers:
     - Click on the .search-trigger button in the nav.
     - Cmd/Ctrl-K from anywhere.
     - "/" from anywhere except inside an input/textarea/contenteditable.
   The overlay lazy-loads Pagefind on first open so non-searchers
   never pay the runtime cost.
   ════════════════════════════════════════════════════════════════ */
(function () {
  // Per-locale strings. Picked off the <html lang="..."> attribute.
  // English is the authoritative source; FR/DE are mirrors.
  const STRINGS = {
    en: {
      placeholder: 'Search the site…',
      close: 'Close',
      navigate: 'navigate',
      open: 'open',
      escClose: 'close',
      noResults: 'No results for',
      typeToSearch: 'Type to search across pages, FAQ entries, glossary terms, and more.',
      resultsCount: (n) => `${n} ${n === 1 ? 'result' : 'results'}`,
      loading: 'Loading search…',
      loadError: 'Search is unavailable. Reload the page to try again.',
      searchLabel: 'Search',
      filterLabel: 'Filter results by type',
      filterAll: 'All',
      filterPages: 'Pages',
      filterPeople: 'People',
    },
    fr: {
      placeholder: 'Rechercher sur le site…',
      close: 'Fermer',
      navigate: 'naviguer',
      open: 'ouvrir',
      escClose: 'fermer',
      noResults: 'Aucun résultat pour',
      typeToSearch: 'Tapez pour chercher dans les pages, la FAQ, le glossaire, et plus encore.',
      resultsCount: (n) => `${n} résultat${n === 1 ? '' : 's'}`,
      loading: 'Chargement de la recherche…',
      loadError: 'La recherche est indisponible. Rechargez la page pour réessayer.',
      searchLabel: 'Rechercher',
      filterLabel: 'Filtrer les résultats par type',
      filterAll: 'Tout',
      filterPages: 'Pages',
      filterPeople: 'Personnes',
    },
    de: {
      placeholder: 'Website durchsuchen…',
      close: 'Schließen',
      navigate: 'navigieren',
      open: 'öffnen',
      escClose: 'schließen',
      noResults: 'Keine Treffer für',
      typeToSearch: 'Tippen Sie, um Seiten, FAQ-Einträge, Glossarbegriffe und mehr zu durchsuchen.',
      resultsCount: (n) => `${n} ${n === 1 ? 'Treffer' : 'Treffer'}`,
      loading: 'Suche wird geladen…',
      loadError: 'Suche nicht verfügbar. Seite neu laden und erneut versuchen.',
      searchLabel: 'Suchen',
      filterLabel: 'Ergebnisse nach Typ filtern',
      filterAll: 'Alle',
      filterPages: 'Seiten',
      filterPeople: 'Personen',
    },
  };

  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const t = STRINGS[lang] || STRINGS.en;

  // ── Platform-aware shortcut label ────────────────────────────
  // Mac users have a ⌘ key; everyone else uses Ctrl. The button's
  // `title` tooltip is rewritten on load so each visitor sees the
  // shortcut that applies to *their* keyboard, not a generic
  // "Cmd/Ctrl-K" mash-up that adds visual noise.
  const isMac = /mac|iphone|ipad|ipod/i.test(
    navigator.platform || navigator.userAgent || ''
  );
  const shortcutLabel = isMac ? '⌘ K' : 'Ctrl K';

  // ── Highlight-on-landing bootstrap ────────────────────────────
  // When a search result link navigates here with a
  // `?pagefind-highlight=<term>` query, dynamically import
  // Pagefind's mark.js wrapper and highlight every match of the
  // term. The script injects a default `:where(.pagefind-
  // highlight){background:yellow;color:black}` style. If the URL
  // has no fragment to scroll to, also scroll the first highlight
  // into view so the visitor lands on the matched term, not on
  // the page top.
  //
  // We instantiate but deliberately DON'T call `.highlight()` on the
  // result — the constructor runs `this.highlight()` itself, so a
  // second call wraps every already-marked term in a nested second
  // `<mark>` (issue #118). Screen readers announce the inner mark
  // twice; visual rendering is unaffected.
  if (window.location.search.indexOf('pagefind-highlight=') !== -1) {
    import('/pagefind/pagefind-highlight.js')
      .then((mod) => {
        new mod.default();
        if (!window.location.hash) {
          requestAnimationFrame(() => {
            const first = document.querySelector('.pagefind-highlight');
            if (first) {
              first.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
        }
      })
      .catch((e) => console.warn('Pagefind highlight failed', e));
  }

  // ── State ────────────────────────────────────────────────────
  let pagefind = null;           // The loaded Pagefind module
  let pagefindError = false;     // Set if the index fails to load
  let pagefindPromise = null;    // Memoised loader
  let overlay = null;            // The injected DOM
  let lastFocus = null;          // Restore on close
  let debounceTimer = 0;
  let activeIndex = -1;          // Highlighted result row
  let currentResults = [];       // The hits currently RENDERED, so activeIndex
                                 // and the Enter handler index the same rows
                                 // the visitor can see under the active filter.
  let allHits = [];              // Every hit from the last search, unfiltered
  let currentQuery = '';         // Kept so a chip can re-render without a re-query
  let activeFilter = 'all';      // 'all' | 'page' | 'bio'

  // Last error from Pagefind, surfaced in the overlay's meta line
  // alongside the user-facing message so a maintainer reading over
  // a user's shoulder can see what actually broke.
  let pagefindErrorMessage = '';

  // ── Lazy-load Pagefind ────────────────────────────────────────
  // On first open we dynamically import the index runtime. Errors
  // (e.g. missing /pagefind/ in dev) surface as a friendly inline
  // message; nothing else on the page is affected.
  function loadPagefind() {
    if (pagefindPromise) return pagefindPromise;
    pagefindPromise = (async () => {
      try {
        const mod = await import('/pagefind/pagefind.js');
        // mod.init() doesn't wait for the WASM to load — that
        // happens lazily on first .search() — but calling it lets
        // us set options before the first query.
        await mod.init();
        // Opt into the URL-based highlight feature. With this set,
        // Pagefind appends `?pagefind-highlight=<term>` to every
        // sub-result URL. The destination page's highlight script
        // (the bootstrap block at the top of this file) reads the
        // param and marks the matched term — so the visitor lands
        // on the anchored section AND sees the matched word
        // highlighted in yellow.
        await mod.options({ highlightParam: 'pagefind-highlight' });
        pagefind = mod;
        return mod;
      } catch (e) {
        pagefindError = true;
        pagefindErrorMessage = String(e && e.message ? e.message : e);
        console.error('Pagefind failed to load', e);
        throw e;
      }
    })();
    return pagefindPromise;
  }

  // ── Build the overlay DOM (once, on first open) ──────────────
  function buildOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.className = 'search-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', t.searchLabel);
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="search-backdrop" data-search-close></div>
      <div class="search-panel glass" role="document">
        <div class="search-header">
          <svg class="search-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input class="search-input" type="search" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" placeholder="${t.placeholder}" aria-label="${t.searchLabel}" aria-controls="search-results-list" aria-expanded="false" aria-autocomplete="list">
          <button class="search-close" type="button" aria-label="${t.close}" data-search-close>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="search-filters" role="group" aria-label="${t.filterLabel}" data-search-filters hidden>
          <button type="button" class="search-filter" data-search-filter="all" aria-pressed="true"></button>
          <button type="button" class="search-filter" data-search-filter="page" aria-pressed="false"></button>
          <button type="button" class="search-filter" data-search-filter="bio" aria-pressed="false"></button>
        </div>
        <div class="search-meta" aria-live="polite" aria-atomic="true"></div>
        <ul class="search-results" id="search-results-list" role="listbox" aria-label="${t.searchLabel}"></ul>
        <div class="search-hints">
          <span><kbd>↑</kbd><kbd>↓</kbd> ${t.navigate}</span>
          <span><kbd>↵</kbd> ${t.open}</span>
          <span><kbd>Esc</kbd> ${t.escClose}</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const input = overlay.querySelector('.search-input');
    const list = overlay.querySelector('.search-results');
    const meta = overlay.querySelector('.search-meta');

    // Idle state — empty input shows the prompt.
    meta.textContent = t.typeToSearch;

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => runSearch(input.value.trim()), 120);
    });

    // Keyboard navigation between results.
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { close(); return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveActive(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveActive(-1);
      } else if (
        e.key === 'Enter' && activeIndex >= 0 && currentResults[activeIndex] &&
        // A focused filter chip keeps its own Enter: swallowing it here would
        // open the highlighted result instead of applying the filter.
        !e.target.closest('[data-search-filter]')
      ) {
        e.preventDefault();
        const a = list.children[activeIndex]?.querySelector('a');
        if (a) a.click();
      }
    });

    overlay.addEventListener('click', (e) => {
      // Filter chips re-render from the hits already in hand, so Pagefind is
      // never re-invoked and the ranking is untouched. Keyed off
      // data-search-filter rather than the styling class, per the
      // .members-mentorship-chip collision in #862.
      const chip = e.target.closest('[data-search-filter]');
      if (chip) {
        activeFilter = chip.dataset.searchFilter;
        activeIndex = -1;
        renderResults(allHits, currentQuery);
        return;
      }

      // Close on the explicit close button / backdrop, AND on any
      // result-link click. Without the latter, the overlay would
      // stay open after navigation: same-page hash-only links
      // don't reload, so the visitor would see the modal still
      // covering the page they're trying to read.
      if (
        e.target.closest('[data-search-close]') ||
        e.target.closest('.search-results a')
      ) {
        close();
      }
    });

    return overlay;
  }

  // ── Query + render ───────────────────────────────────────────
  async function runSearch(query) {
    const meta = overlay.querySelector('.search-meta');
    const list = overlay.querySelector('.search-results');
    const input = overlay.querySelector('.search-input');

    activeIndex = -1;
    currentResults = [];
    allHits = [];
    currentQuery = query;
    // Every query starts from All. Carrying a filter across queries would let
    // a chip pressed two searches ago silently hide the new results, and the
    // chip row is not visible while the reader is typing to remind them.
    activeFilter = 'all';

    if (!query) {
      meta.textContent = t.typeToSearch;
      list.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      hideFilters();
      return;
    }

    if (pagefindError) {
      meta.textContent = pagefindErrorMessage
        ? `${t.loadError} (${pagefindErrorMessage})`
        : t.loadError;
      list.innerHTML = '';
      hideFilters();
      return;
    }

    try {
      const pf = await loadPagefind();
      // Pagefind v1 ships one shard per language and picks the
      // active one from <html lang> at init time. No filter needed
      // on the search call — passing `{filters: {language: lang}}`
      // is interpreted as "filter by a `language` metadata field
      // on each page", which we never set, so it threw / returned
      // nothing. Empty options is correct.
      const search = await pf.search(query);
      // search.results is a Promise array of hit handles. Resolve
      // the first ~12 — Pagefind returns ranked results lazily.
      const hits = await Promise.all(search.results.slice(0, 12).map((r) => r.data()));
      allHits = hits;
      renderResults(hits, query);
    } catch (e) {
      pagefindErrorMessage = String(e && e.message ? e.message : e);
      console.error('Pagefind search failed', e);
      meta.textContent = `${t.loadError} (${pagefindErrorMessage})`;
      list.innerHTML = '';
      hideFilters();
    }
  }

  function isBioHit(hit) {
    return !!(hit.meta && hit.meta.kind === 'bio');
  }

  function hideFilters() {
    const row = overlay && overlay.querySelector('[data-search-filters]');
    if (row) row.hidden = true;
    activeFilter = 'all';
  }

  // The chip row only earns its space when both types are present. A query
  // that returns pages alone, or people alone, gets no row and no decision
  // to make.
  function syncFilters(hits) {
    const row = overlay.querySelector('[data-search-filters]');
    const people = hits.filter(isBioHit).length;
    const pages = hits.length - people;

    if (!pages || !people) {
      row.hidden = true;
      activeFilter = 'all';
      return;
    }

    row.hidden = false;
    const counts = { all: hits.length, page: pages, bio: people };
    const labels = { all: t.filterAll, page: t.filterPages, bio: t.filterPeople };
    row.querySelectorAll('[data-search-filter]').forEach((chip) => {
      const kind = chip.dataset.searchFilter;
      chip.textContent = `${labels[kind]} (${counts[kind]})`;
      chip.setAttribute('aria-pressed', kind === activeFilter ? 'true' : 'false');
    });
  }

  function renderResults(hits, query) {
    const meta = overlay.querySelector('.search-meta');
    const list = overlay.querySelector('.search-results');
    const input = overlay.querySelector('.search-input');

    if (hits.length === 0) {
      meta.textContent = `${t.noResults} "${query}"`;
      list.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      hideFilters();
      currentResults = [];
      return;
    }

    // syncFilters can clear activeFilter back to 'all' when the row is not
    // warranted, so partition after it has run, not before.
    syncFilters(hits);
    const shown = activeFilter === 'all'
      ? hits
      : hits.filter((hit) => isBioHit(hit) === (activeFilter === 'bio'));

    currentResults = shown;
    meta.textContent = t.resultsCount(shown.length);
    input.setAttribute('aria-expanded', 'true');

    list.innerHTML = shown.map((hit, i) => renderHit(hit, i)).join('');
  }

  // Per-hit renderer. Directory bio hits get a richer card with the
  // member's photo / country flag / WG chips. Everything else falls
  // back to the plain title + section + excerpt layout.
  function renderHit(hit, i) {
    if (hit.meta && hit.meta.kind === 'bio') {
      return renderBioHit(hit, i);
    }
    return renderPageHit(hit, i);
  }

  function renderPageHit(hit, i) {
    // Pagefind populates meta.title from the page's <title>; the
    // section heading comes via sub_results[0].title if the hit
    // matched within an anchored sub-section.
    const title = escapeHtml(hit.meta.title || hit.url);
    const sub = hit.sub_results && hit.sub_results[0];
    const heading = sub ? escapeHtml(sub.title) : '';
    const url = sub ? sub.url : hit.url;
    const excerpt = sub ? sub.excerpt : hit.excerpt;
    return `
      <li role="option" aria-selected="false" id="search-result-${i}">
        <a href="${url}">
          <div class="search-result-head">
            <span class="search-result-title">${title}</span>
            ${heading ? `<span class="search-result-sep">·</span><span class="search-result-section">${heading}</span>` : ''}
          </div>
          <div class="search-result-excerpt">${excerpt}</div>
        </a>
      </li>
    `;
  }

  function renderBioHit(hit, i) {
    // Bio stubs (search/bios/<lang>/<slug>.html) set:
    //   meta.kind == 'bio'
    //   meta.title       — Dr Name (from the stub's <title>, sans " — NetSec directory")
    //   meta.photo       — relative path to the headshot
    //   meta.country     — ISO 3166-1 alpha-2 country code (lowercase)
    //   meta.affiliation — text
    //   meta.role        — "Management Committee · Switzerland", or "" for non-MC
    //   meta.wgs         — comma-separated WG numbers, e.g. "2,3"
    const rawTitle = (hit.meta.title || '').replace(/\s+—\s+NetSec directory$/, '');
    const name = escapeHtml(rawTitle);
    const affiliation = escapeHtml(hit.meta.affiliation || '');
    const role = escapeHtml(hit.meta.role || '');
    const country = (hit.meta.country || '').toLowerCase().replace(/[^a-z]/g, '');
    const photo = hit.meta.photo || '';
    const wgs = (hit.meta.wgs || '').split(',').map((s) => s.trim()).filter(Boolean);
    // Rewrite the stub URL to the canonical directory anchor.
    // Pagefind v1 doesn't have a per-page URL-override mechanism,
    // so we do it client-side: parse the stub URL's path for the
    // locale + slug, build /people.html#<slug> (locale-aware),
    // and carry the highlight query through if present.
    const url = canonicalBioUrl(hit.url) || hit.url;

    const flagImg = country
      ? `<img class="search-bio-flag" src="https://flagcdn.com/h20/${country}.png" alt="" loading="lazy">`
      : '';
    const photoEl = photo
      ? `<img class="search-bio-photo" src="${escapeHtml(photo)}" alt="" loading="lazy">`
      : `<span class="search-bio-photo search-bio-photo-fallback" aria-hidden="true">${initialsFor(rawTitle)}</span>`;
    const wgChips = wgs
      .map((w) => `<span class="search-bio-wg">WG${escapeHtml(w)}</span>`)
      .join('');
    const subline = role || affiliation;

    return `
      <li role="option" aria-selected="false" id="search-result-${i}" class="search-bio">
        <a href="${url}">
          ${photoEl}
          <div class="search-bio-text">
            <div class="search-bio-head">
              <span class="search-bio-name">${name}</span>
              ${flagImg}
            </div>
            ${subline ? `<div class="search-bio-subline">${subline}</div>` : ''}
            ${role && affiliation && role !== affiliation
                ? `<div class="search-bio-affiliation">${affiliation}</div>` : ''}
            ${wgChips ? `<div class="search-bio-wgs">${wgChips}</div>` : ''}
          </div>
        </a>
      </li>
    `;
  }

  // Rewrites a Pagefind bio-stub URL to the canonical directory
  // entry. Stubs live at /search/bios/<lang>/<slug>.html and are
  // never visited; the overlay link points straight at
  // /people.html#<slug> (or /people.<lang>.html#<slug>) with the
  // pagefind-highlight query carried through.
  //   /search/bios/en/arthur-laudrain.html?pagefind-highlight=foo
  //     → /people.html?pagefind-highlight=foo#arthur-laudrain
  function canonicalBioUrl(stubUrl) {
    if (!stubUrl) return null;
    const m = stubUrl.match(
      /\/search\/bios\/([a-z]{2})\/([^/?#.]+)\.html(\?[^#]*)?/
    );
    if (!m) return null;
    const [, bioLang, slug, query] = m;
    const peoplePath = bioLang === 'en'
      ? '/people.html'
      : `/people.${bioLang}.html`;
    return `${peoplePath}${query || ''}#${slug}`;
  }

  // Two-letter initials for the photo fallback. The shared rule lives
  // in window.netsecInitials (#1194); this wrapper only adds the HTML
  // escaping the search-result template string needs.
  function initialsFor(name) {
    return escapeHtml(window.netsecInitials(name));
  }

  function moveActive(delta) {
    const list = overlay.querySelector('.search-results');
    const items = list.children;
    if (items.length === 0) return;
    activeIndex = (activeIndex + delta + items.length) % items.length;
    for (let i = 0; i < items.length; i++) {
      const isActive = i === activeIndex;
      items[i].classList.toggle('is-active', isActive);
      items[i].setAttribute('aria-selected', isActive ? 'true' : 'false');
    }
    const active = items[activeIndex];
    if (active) {
      const input = overlay.querySelector('.search-input');
      input.setAttribute('aria-activedescendant', active.id);
      active.scrollIntoView({ block: 'nearest' });
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ── Open / close ─────────────────────────────────────────────
  function open() {
    if (overlay && !overlay.hidden) return;
    lastFocus = document.activeElement;
    buildOverlay();
    overlay.hidden = false;
    document.body.classList.add('search-open');
    // Pre-load the index in the background so the first keystroke
    // is fast (we don't await; if it fails the input still works
    // and surfaces the error).
    loadPagefind().catch(() => {});
    requestAnimationFrame(() => {
      overlay.querySelector('.search-input').focus();
    });
  }

  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.body.classList.remove('search-open');
    const input = overlay.querySelector('.search-input');
    if (input) input.value = '';
    const list = overlay.querySelector('.search-results');
    if (list) list.innerHTML = '';
    const meta = overlay.querySelector('.search-meta');
    if (meta) meta.textContent = t.typeToSearch;
    hideFilters();
    activeIndex = -1;
    currentResults = [];
    allHits = [];
    currentQuery = '';
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    }
  }

  // ── Trigger wiring ───────────────────────────────────────────

  // Rewrite the .search-trigger button titles to show the visitor's
  // platform shortcut (⌘ K on Mac, Ctrl K elsewhere). The HTML
  // ships a generic "Search (Cmd/Ctrl-K)" placeholder; the rewrite
  // happens once on page load.
  (function setTriggerTitles() {
    const title = `${t.searchLabel} (${shortcutLabel})`;
    document.querySelectorAll('.search-trigger').forEach((btn) => {
      btn.setAttribute('title', title);
      btn.setAttribute('aria-keyshortcuts', isMac ? 'Meta+K' : 'Control+K');
    });
  })();

  // 1. Click on the magnifying-glass button in the nav.
  document.addEventListener('click', (e) => {
    if (e.target.closest('.search-trigger')) {
      e.preventDefault();
      open();
    }
  });

  // 2. Cmd/Ctrl-K from anywhere.
  // 3. "/" from anywhere EXCEPT inside an input / textarea / contenteditable.
  //
  // For Cmd/Ctrl-K we check both e.key and e.code so the shortcut
  // still works on layouts where the printed `k` glyph isn't at the
  // physical KeyK position (Dvorak, AZERTY in some browsers, etc.).
  // We also listen on `window` rather than `document` because some
  // browser extensions install higher-priority listeners on document
  // that swallow Cmd-K before it reaches a document-level handler.
  function isCmdK(e) {
    if (!(e.metaKey || e.ctrlKey)) return false;
    if (e.altKey) return false;
    const key = (e.key || '').toLowerCase();
    return key === 'k' || e.code === 'KeyK';
  }

  window.addEventListener('keydown', (e) => {
    if (isCmdK(e)) {
      e.preventDefault();
      open();
      return;
    }
    if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const tag = (e.target.tagName || '').toLowerCase();
      const editable = e.target.isContentEditable;
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || editable) return;
      e.preventDefault();
      open();
    }
  });

  // Expose for debugging / programmatic open if ever needed.
  window.netsecSearch = { open, close };
})();

/* What's New banner — sparingly-used site-wide announcement.
   ──────────────────────────────────────────────────────────
   Reads /data/whats-new.json. If `active: true` and the visitor
   hasn't dismissed this exact `version`, renders a dismissible
   banner at the top of <body>. Dismissal saves to
   localStorage('netsec-whats-new-dismissed-<version>') so the
   visitor sees the banner once and never again for that release.

   Used sparingly per CLAUDE.md §14 — at most 3-4 activations per
   year, on releases that introduce something a returning visitor
   would want to know about without scrolling for it. NOT used for
   quality patches, structural refactors, or release-infrastructure
   changes. Maintainer flips `active` true → false manually. */
(function () {
  fetch('/data/whats-new.json', { cache: 'no-cache' })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data || !data.active || !data.version) return;
      let dismissed = null;
      try { dismissed = localStorage.getItem('netsec-whats-new-dismissed-' + data.version); } catch (e) {}
      if (dismissed) return;
      renderWhatsNewBanner(data);
    })
    .catch(() => { /* JSON 404 or parse error — silent no-op */ });

  function renderWhatsNewBanner(data) {
    const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    const headline = (data.headline && (data.headline[lang] || data.headline.en)) || '';
    if (!headline) return;
    const ctaLabel = data.cta && data.cta.i18n && (data.cta.i18n[lang] || data.cta.i18n.en);
    // href can be a plain string (same URL for every locale, e.g. a
    // GitHub release page) OR a {en, fr, de} object (locale-specific
    // landing pages, e.g. /essc-2026.html vs .fr.html vs .de.html).
    const rawHref = data.cta && data.cta.href;
    const ctaHref = typeof rawHref === 'string'
      ? rawHref
      : (rawHref && (rawHref[lang] || rawHref.en)) || '';

    const banner = document.createElement('div');
    banner.className = 'whats-new-banner';
    banner.setAttribute('role', 'status');

    const sparkle = document.createElement('span');
    sparkle.className = 'whats-new-sparkle';
    sparkle.setAttribute('aria-hidden', 'true');
    sparkle.textContent = '✦';
    banner.appendChild(sparkle);

    const text = document.createElement('span');
    text.className = 'whats-new-text';
    text.textContent = headline;
    banner.appendChild(text);

    if (ctaLabel && ctaHref) {
      const cta = document.createElement('a');
      cta.className = 'whats-new-cta';
      cta.href = ctaHref;
      cta.textContent = ctaLabel;
      if (data.cta.external) {
        cta.target = '_blank';
        cta.rel = 'noopener';
      }
      banner.appendChild(cta);
    }

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'whats-new-close';
    const closeLabel = { en: 'Dismiss', fr: 'Fermer', de: 'Schließen' }[lang] || 'Dismiss';
    close.setAttribute('aria-label', closeLabel);
    close.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    close.addEventListener('click', () => {
      try { localStorage.setItem('netsec-whats-new-dismissed-' + data.version, '1'); } catch (e) {}
      banner.classList.add('whats-new-banner--closing');
      // Keep --whats-new-h set through the slide-out animation so
      // content doesn't snap up while the banner is visibly leaving.
      // Clear it (so ribbon + nav slide back up to top:0) only after
      // the animation completes.
      setTimeout(() => {
        document.documentElement.style.removeProperty('--whats-new-h');
        banner.remove();
      }, 240);
    });
    banner.appendChild(close);

    // Insert at the very top of <body>. The banner is position: fixed,
    // so insertion order doesn't change the visual stack; what matters
    // is the body padding-top and the ribbon/nav top offsets, both
    // composed against --whats-new-h via CSS calc().
    document.body.insertBefore(banner, document.body.firstChild);

    // Measure and publish the banner height as --whats-new-h on the
    // documentElement so the existing top-stack math (body padding,
    // ribbon top, nav top) picks it up. Same pattern as --ribbon-h.
    // ResizeObserver covers wrap-state changes (the headline can
    // re-wrap on narrow viewports or as fonts swap).
    const syncBannerHeight = () => {
      const h = banner.offsetHeight;
      if (h > 0) {
        document.documentElement.style.setProperty('--whats-new-h', h + 'px');
      }
    };
    syncBannerHeight();
    if (document.readyState !== 'complete') {
      window.addEventListener('load', syncBannerHeight, { once: true });
    }
    window.addEventListener('resize', syncBannerHeight, { passive: true });
    if (typeof ResizeObserver === 'function') {
      try { new ResizeObserver(syncBannerHeight).observe(banner); } catch (e) {}
    }
  }
})();

/* ── Member-card popover: a reusable, site-wide component ──────────────
   The floating profile card (photo, name, role / WG badges, country,
   contacts, "View full profile" CTA) that appears on hover / focus over
   a person's name. Two surfaces use it: this module wires plain
   `data-member` anchors (Summer School faculty, any static page), and
   the ESSC programme renderer (essc-2026.html) calls the same core after
   its own fuzzy speaker-name matcher has resolved a name to a bios
   record. To keep one copy of the popover machinery, the card core is
   exposed on the global below and both surfaces drive it:

       window.netsecMemberCard = {
         show(anchorEl, memberObj, opts),   // build / populate / position / open
         hide(),                            // close the shared popover now
       };

   `memberObj` is a bios.json member record. `opts` is optional and lets a
   caller tune the few locale / feature differences without forking the
   card:

       opts.ctaHref        explicit "View full profile" href. Default: the
                           anchor's own href, falling back to people.html#id.
       opts.ariaLabel      already-localised popover aria-label string.
                           Default: netsecT('Member profile').
       opts.roleLabel      maps a role string to display text. Default:
                           netsecT (this module's anchors translate role
                           chips). The ESSC renderer passes identity so its
                           raw Indico-sourced role strings stay verbatim.
       opts.wgPrefix       when set, append bare WG-number chips ("WG3"
                           localised to "GT3" / "AG3") for member.wgs not
                           already named by a role. Default: omitted (this
                           module skips the prefix the static pages don't
                           translate).
       opts.contactLabels  per-kind aria-label overrides for the contact
                           icons. Default: netsecT over the English label.

   The popover markup and the `.essc-member-card*` styling are shared, so
   both surfaces render through one stylesheet block. The class names keep
   their `essc-` prefix for now (CSS rename is tracked separately). The
   authored `href` on every anchor is the graceful fallback: with JS off,
   an unknown id, or a browser without the Popover API, the anchor is just
   a deep link into the directory, so nothing is ever a dead end. */
window.netsecMemberCard = (function () {
  const T = (s) => (window.netsecT && window.netsecT(s)) || s;
  const peopleUrl = 'people.html';

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (attrs[k] == null) continue;
      if (k === 'class') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    for (const c of kids) if (c != null) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    return n;
  }

  // Brand glyphs, mirrored from people.html. `style` says whether the
  // path is stroked or filled. The full set (including twitter /
  // mastodon) lives here so the ESSC programme, which surfaces those two,
  // shares one glyph table; a member without the field never renders the
  // icon, so the extra entries are inert on surfaces that don't use them.
  const CONTACT_GLYPHS = {
    email:   { style: 'stroke', path: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>' },
    website: { style: 'stroke', path: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20"/>' },
    orcid:   { style: 'fill',   path: '<path fill-rule="evenodd" d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947 0 .525-.422.947-.947.947a.95.95 0 01-.947-.947c0-.516.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 4.022-2.484 4.022-3.722 0-2.016-1.284-3.722-4.094-3.722H12.8z"/>' },
    linkedin:{ style: 'fill',   path: '<path fill-rule="evenodd" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.063 2.063 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>' },
    twitter: { style: 'fill',   path: '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>' },
    bluesky: { style: 'fill',   path: '<path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.81 8.477 7.823 4.308 4.557-5.073 1.082-6.498-2.83-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.829.624-5.79.624-6.479 0-.688-.139-1.86-.902-2.203-.659-.299-1.664-.621-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z"/>' },
    mastodon:{ style: 'fill',   path: '<path fill-rule="evenodd" d="M23.27 5.31c-.35-2.58-2.62-4.61-5.31-5C17.51.25 15.79 0 11.81 0h-.03c-3.98 0-4.83.25-5.29.31C3.88.7 1.5 2.52.92 5.13.64 6.41.61 7.84.66 9.14c.07 1.88.09 3.74.26 5.61.12 1.24.32 2.47.62 3.68.55 2.24 2.78 4.1 4.96 4.86 2.34.79 4.85.92 7.26.38.26-.06.53-.13.79-.21.59-.18 1.27-.39 1.77-.75v-1.85a20.28 20.28 0 01-4.71.54c-2.73 0-3.46-1.28-3.67-1.82a5.6 5.6 0 01-.32-1.43c1.51.36 3.07.55 4.63.55l1.13-.01c1.57-.04 3.22-.12 4.77-.42l.11-.02c2.43-.46 4.75-1.92 4.99-5.6.01-.15.03-1.52.03-1.67 0-.51.17-3.63-.02-5.55zm-3.75 9.19h-2.56V8.29c0-1.31-.55-1.98-1.67-1.98-1.23 0-1.85.79-1.85 2.35v3.4h-2.55V8.66c0-1.56-.62-2.35-1.85-2.35-1.11 0-1.67.67-1.67 1.98v6.22H4.82V8.1c0-1.31.34-2.35 1.01-3.12.7-.77 1.61-1.16 2.74-1.16 1.31 0 2.3.5 2.96 1.5l.64 1.06.64-1.06c.66-1 1.65-1.5 2.96-1.5 1.13 0 2.04.39 2.74 1.16.68.77 1.01 1.81 1.01 3.12v6.4z"/>' },
  };
  // Default contact aria-labels. A caller can override any of these via
  // opts.contactLabels (the ESSC renderer passes its localised set).
  const DEFAULT_CONTACT_LABELS = {
    email: 'Email', website: 'Website', orcid: 'ORCID iD',
    linkedin: 'LinkedIn', twitter: 'X', bluesky: 'Bluesky', mastodon: 'Mastodon',
  };

  function normaliseOrcid(raw) {
    if (!raw) return null;
    let s = String(raw).trim().replace(/^(?:https?:\/\/)?(?:sandbox\.)?orcid\.org\//i, '');
    s = s.split('?')[0].split('#')[0].replace(/\/+$/, '').trim();
    if (/^\d{15}[\dX]$/i.test(s)) s = `${s.slice(0,4)}-${s.slice(4,8)}-${s.slice(8,12)}-${s.slice(12,16)}`;
    return /^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/i.test(s) ? s.toUpperCase() : null;
  }

  function contactIcon(kind, href, label) {
    const a = el('a', { class: 'essc-member-card-contact', href, 'aria-label': label, title: label });
    if (kind === 'orcid') a.classList.add('is-orcid');
    if (href.startsWith('http')) { a.target = '_blank'; a.rel = 'noopener'; }
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const g = CONTACT_GLYPHS[kind];
    if (g.style === 'stroke') {
      svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '1.9'); svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
    } else { svg.setAttribute('fill', 'currentColor'); }
    svg.innerHTML = g.path;
    a.appendChild(svg);
    return a;
  }

  // ── shared popover element ──────────────────────────────────────
  // One <div popover="auto"> appended to <body>, reused across every
  // member-linked name on the page. The Popover API gives light-dismiss
  // (click outside) and Escape-to-close for free, plus top-layer
  // rendering so the card escapes any clipped ancestor. We position it
  // ourselves with getBoundingClientRect so it works in every browser
  // that ships popover, with no dependency on CSS anchor positioning.
  let cardEl = null, hideTimer = null, currentMember = null, openScrollY = 0;
  let cardAriaLabel = null;   // the aria-label requested by the most recent show()
  const HIDE_DELAY_MS = 180;

  function cancelHide() { if (hideTimer != null) { clearTimeout(hideTimer); hideTimer = null; } }
  function scheduleHide() {
    cancelHide();
    hideTimer = setTimeout(() => { if (cardEl && cardEl.matches(':popover-open')) cardEl.hidePopover(); }, HIDE_DELAY_MS);
  }

  function ensureCard() {
    if (cardEl) return cardEl;
    if (typeof HTMLElement.prototype.showPopover !== 'function') return null;
    cardEl = el('div', {
      id: 'netsec-member-card', class: 'essc-member-card', popover: 'auto',
      role: 'dialog', 'aria-labelledby': 'netsec-member-card-name', 'aria-label': T('Member profile'),
    });
    // Hovering the card itself keeps it open even after the pointer
    // leaves the originating anchor, so moving onto the card to click a
    // contact icon doesn't trip the hide timer.
    cardEl.addEventListener('mouseenter', cancelHide);
    cardEl.addEventListener('mouseleave', scheduleHide);
    cardEl.addEventListener('toggle', (e) => { if (e.newState === 'closed') { currentMember = null; cancelHide(); } });
    // The card is position:fixed, so it stays put while the page scrolls
    // and the anchor scrolls away underneath. Dismiss on a meaningful
    // scroll only: the 24px threshold ignores iOS rubber-band bounces and
    // stray sub-pixel scrolls that can fire right after a tap. The
    // reference scrollY is reset each time a new popover open completes.
    window.addEventListener('scroll', () => {
      if (!cardEl || !cardEl.matches(':popover-open')) return;
      if (Math.abs(window.scrollY - openScrollY) < 24) return;
      cancelHide(); cardEl.hidePopover();
    }, { passive: true });
    document.body.appendChild(cardEl);
    return cardEl;
  }

  function populate(card, m, opts) {
    const roleLabel = opts.roleLabel || T;
    const contactLabels = opts.contactLabels || {};
    card.innerHTML = '';
    const inner = el('div', { class: 'essc-member-card-inner' });
    if (m.photo) {
      const img = el('img', { class: 'essc-member-card-photo', src: m.photo, alt: '', loading: 'lazy', decoding: 'async' });
      const webp = window.netsecWebp && window.netsecWebp(m.photo);
      inner.appendChild(webp
        ? el('picture', { class: 'essc-member-card-picture' }, el('source', { type: 'image/webp', srcset: webp }), img)
        : img);
    } else {
      inner.appendChild(el('div', { class: 'essc-member-card-photo essc-member-card-photo-placeholder', 'aria-hidden': 'true' }));
    }
    const text = el('div', { class: 'essc-member-card-text' });
    text.appendChild(el('p', { class: 'essc-member-card-name', id: 'netsec-member-card-name' }, m.name || ''));
    if (m.position)    text.appendChild(el('p', { class: 'essc-member-card-role' }, m.position));
    if (m.affiliation) text.appendChild(el('p', { class: 'essc-member-card-aff' }, m.affiliation));

    // Role badges. Each role string flows through opts.roleLabel (this
    // module's default translates; the ESSC renderer passes identity so
    // its raw role strings stay verbatim). When opts.wgPrefix is set, bare
    // WG-number chips ("WG3" → localised prefix) are appended for any
    // member.wgs not already named by a role, deduplicated so a "WG1
    // Leader" role suppresses a separate "WG1" chip.
    const badges = [];
    const knownWgs = new Set();
    for (const r of (m.roles || [])) {
      badges.push({ text: roleLabel(r), kind: 'role' });
      const mm = /WG\s*([1-4])/i.exec(r);
      if (mm) knownWgs.add(Number(mm[1]));
    }
    if (opts.wgPrefix) {
      for (const n of (m.wgs || [])) {
        if (knownWgs.has(n)) continue;
        badges.push({ text: `${opts.wgPrefix}${n}`, kind: 'wg' });
      }
    }
    if (badges.length) {
      const row = el('div', { class: 'essc-member-card-badges' });
      for (const b of badges) row.appendChild(el('span', { class: 'essc-member-card-badge' + (b.kind === 'wg' ? ' is-wg' : '') }, b.text));
      text.appendChild(row);
    }
    if (m.country) {
      const c = el('p', { class: 'essc-member-card-country' });
      if (m.country_code) c.appendChild(el('img', { src: `https://flagcdn.com/h20/${m.country_code}.png`, alt: '', width: '18', height: '12', loading: 'lazy' }));
      c.appendChild(document.createTextNode(m.country));
      text.appendChild(c);
    }
    if (m.bio) text.appendChild(el('p', { class: 'essc-member-card-bio' }, m.bio));

    // Social-link icons, order mirroring people.html. Each entry lands
    // only if the member has a non-empty value; the row is omitted when
    // none do. Labels resolve from opts.contactLabels, then the English
    // default routed through netsecT.
    const label = (kind) => contactLabels[kind] || T(DEFAULT_CONTACT_LABELS[kind]);
    const orcidId = normaliseOrcid(m.orcid);
    const contacts = [
      m.email    && ['email',    'mailto:' + m.email, label('email')],
      m.website  && ['website',  m.website,           label('website')],
      orcidId    && ['orcid',    'https://orcid.org/' + orcidId, label('orcid')],
      m.linkedin && ['linkedin', m.linkedin,          label('linkedin')],
      m.twitter  && ['twitter',  m.twitter,           label('twitter')],
      m.bluesky  && ['bluesky',  m.bluesky,           label('bluesky')],
      m.mastodon && ['mastodon', m.mastodon,          label('mastodon')],
    ].filter(Boolean);
    if (contacts.length) {
      const row = el('div', { class: 'essc-member-card-contacts' });
      for (const [k, h, l] of contacts) row.appendChild(contactIcon(k, h, l));
      text.appendChild(row);
    }
    inner.appendChild(text);
    card.appendChild(inner);

    const footer = el('div', { class: 'essc-member-card-footer' });
    const ctaHref = opts.ctaHref || (peopleUrl + '#' + m.id);
    const cta = el('a', { class: 'essc-member-card-cta', href: ctaHref }, opts.ctaLabel || T('View full profile'));
    // Safari Technology Preview (as of May 2026) has a bug where clicks on
    // an <a href> inside an open popover="auto" fire the click event but
    // the default navigation gets silently swallowed by the top-layer
    // machinery, leaving the visitor still on the current page with no
    // error. The workaround is harmless elsewhere (preventDefault +
    // JS-driven nav is functionally identical to letting the <a> default
    // fire), so it ships unconditionally rather than gated on a UA sniff.
    // Cmd / Ctrl / middle-click pass through so "open in new tab" works.
    cta.addEventListener('click', (e) => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      if (cardEl && cardEl.matches(':popover-open')) cardEl.hidePopover();
      // Defer one tick so Safari can settle the popover-close before
      // assigning location; without it the nav can be rolled back by the
      // still-in-flight top-layer teardown.
      setTimeout(() => { window.location.assign(ctaHref); }, 0);
    });
    footer.appendChild(cta);
    card.appendChild(footer);
  }

  // Show the card for `m`, attached to `anchor`. If the card already shows
  // this exact member, just cancel any pending hide. If it shows a
  // different one, swap content and reposition without close-then-reopen
  // (which would blink). Returns the card element, or null when the
  // Popover API is unavailable (caller should let the link navigate).
  function show(anchor, m, opts) {
    opts = opts || {};
    const card = ensureCard();
    if (!card) return null;
    cancelHide();
    // Keep the popover's aria-label in step with the caller's locale.
    const wantLabel = opts.ariaLabel || T('Member profile');
    if (wantLabel !== cardAriaLabel) { card.setAttribute('aria-label', wantLabel); cardAriaLabel = wantLabel; }
    if (currentMember === m && card.matches(':popover-open')) return card;
    currentMember = m;
    populate(card, m, opts);
    // Pre-position near the anchor so the first paint after showPopover is
    // close, then measure and refine.
    const ar = anchor.getBoundingClientRect();
    card.style.left = ar.left + 'px';
    card.style.top  = (ar.bottom + 6) + 'px';
    if (!card.matches(':popover-open')) card.showPopover();
    openScrollY = window.scrollY;
    const cr = card.getBoundingClientRect();
    const margin = 8, vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
    let left = ar.left + ar.width / 2 - cr.width / 2;
    left = Math.max(margin, Math.min(left, vw - cr.width - margin));
    let top = ar.bottom + 6;
    if (top + cr.height > vh - margin && ar.top - cr.height - 6 >= margin) top = ar.top - cr.height - 6;
    card.style.left = left + 'px';
    card.style.top  = top  + 'px';
    return card;
  }

  function hide() { if (cardEl && cardEl.matches(':popover-open')) { cancelHide(); cardEl.hidePopover(); } }

  return { show, hide, scheduleHide, cancelHide };
})();

/* Auto-wire static `data-member` anchors to the shared card core.
   Any page can turn a name into a hover / focus / click profile card with:

       <a class="member-link" href="people.html#<id>" data-member="<id>">Name</a>

   This block fetches data/bios.json once, builds an id → member map, and
   delegates open / close to window.netsecMemberCard. Role chips translate
   via the card's default (netsecT); the CTA reuses each anchor's own href
   so the directory locale follows what the author linked. */
(function () {
  const anchors = Array.from(document.querySelectorAll('a.member-link[data-member]'));
  if (!anchors.length) return;
  const card = window.netsecMemberCard;
  if (!card) return;

  fetch('data/bios.json', { cache: 'no-cache' })
    .then((r) => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
    .then((bios) => {
      const byId = new Map();
      for (const m of (bios && bios.members) || []) if (m && m.id) byId.set(m.id, m);
      for (const a of anchors) {
        const m = byId.get(a.dataset.member);
        if (!m) continue;                 // unknown id → plain directory link
        a.classList.add('is-wired');
        const opts = { ctaHref: a.getAttribute('href') };
        const open = (e) => {
          if (e.type === 'click') {
            if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            if (!card.show(a, m, opts)) return;   // popover unsupported → let the link navigate
            e.preventDefault();
          } else { card.show(a, m, opts); }
        };
        a.addEventListener('mouseenter', open);
        a.addEventListener('focus', open);
        a.addEventListener('click', open);
        a.addEventListener('mouseleave', card.scheduleHide);
        a.addEventListener('blur', card.scheduleHide);
      }
    })
    .catch((err) => { console.warn('member-card: bios.json fetch failed; links stay as plain directory links:', err); });
})();

/* Site-wide person mentions → hover / focus / click profile card.
   The member-link block above needs an explicit data-member id. This block
   is the general case: any element carrying data-person="<authored name>",
   anywhere on any page, plus any unmarked full-name mention of a directory
   member found in <main> prose, is wired to the shared card. Resolution is
   by a normalised first|last name key (titles, particles and post-nominals
   stripped, the same scheme the ESSC programme and the leadership cards use)
   against data/bios.json. A name that is mentioned today but only joins the
   directory later therefore lights up automatically on the next visit, with
   no edit to the page; a name that is not in the directory stays plain text.
   The .mc-card leadership cards already render the person from the same data,
   so they keep their own presentation and are left alone here. */
(function () {
  const card = window.netsecMemberCard;
  if (!card) return;

  const POSTNOMINALS = new Set(['phd', 'jr', 'sr', 'ii', 'iii', 'iv', 'esq']);
  const PARTICLES = new Set([
    'de', 'del', 'della', 'di', 'da', 'das', 'dos',
    'van', 'von', 'vom', 'der', 'den', 'ter', 'ten',
    'la', 'le', 'el', 'al', 'ibn', 'bin', 'bint', 'zu', 'auf', 'af',
  ]);
  function tokens(name) {
    let s = String(name || '').normalize('NFKD').replace(/[̀-ͯ]/g, '');
    s = s.replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '').replace(/[‘’ʼ'`]/g, '');
    return s.split(/[^A-Za-z]+/).filter(Boolean).map((x) => x.toLowerCase())
      .filter((x) => !POSTNOMINALS.has(x) && !PARTICLES.has(x));
  }
  function nameKey(name) {
    const t = tokens(name);
    return t.length < 2 ? null : t[0] + '|' + t[t.length - 1];
  }
  const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // A member's directory display names (title stripped), longest first, for
  // matching a full name inside arbitrary text. Bare single tokens and very
  // short strings are dropped so only first+last mentions ever match.
  function displayNames(m) {
    const out = [];
    for (const nm of [m.name, ...(m.name_aliases || [])]) {
      const disp = String(nm || '').replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '').trim();
      if (nameKey(disp) && disp.length >= 5 && out.indexOf(disp) === -1) out.push(disp);
    }
    return out.sort((a, b) => b.length - a.length);
  }
  // Wrap the first occurrence of any of `names` inside `root`'s text in a
  // wired <span>, so only the name (not, say, an affiliation line in the same
  // <li>) carries the dotted affordance and the card. Returns true on a wrap.
  function wrapNameIn(root, member, names, hrefOverride) {
    if (!names.length) return false;
    const r = new RegExp('(?<![\\p{L}])(' + names.map(escRe).join('|') + ')(?![\\p{L}])', 'u');
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!n.nodeValue || !r.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
        if (n.parentElement && n.parentElement.closest('a, button')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const node = w.nextNode();
    if (!node) return false;
    const text = node.nodeValue, match = r.exec(text), frag = document.createDocumentFragment();
    if (match.index > 0) frag.appendChild(document.createTextNode(text.slice(0, match.index)));
    const span = document.createElement('span');
    span.textContent = match[1];
    wire(span, member, hrefOverride);
    frag.appendChild(span);
    const end = match.index + match[1].length;
    if (end < text.length) frag.appendChild(document.createTextNode(text.slice(end)));
    node.parentNode.replaceChild(frag, node);
    return true;
  }

  // Ancestors whose text must never be auto-scanned: interactive controls,
  // chrome, forms, code, the directory / programme blocks that render their
  // own member links, and anything already marked or opted out.
  const SKIP_CLOSEST =
    'a, button, nav, footer, label, code, pre, script, style, textarea, ' +
    'option, .member-card, .mc-card, .essc-member-card, .essc-programme, ' +
    '#members-grid, [data-person], [data-no-person], .nav, .site-footer';

  function wire(el, member, hrefOverride) {
    if (el.dataset.personWired) return;
    el.dataset.personWired = '1';
    el.classList.add('has-person-card');
    const opts = { ctaHref: hrefOverride || ('people.html#' + member.id) };
    const open = (e) => {
      if (e.type === 'click') {
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (!card.show(el, member, opts)) return;   // popover unsupported → noop
        e.preventDefault();
      } else { card.show(el, member, opts); }
    };
    el.addEventListener('mouseenter', open);
    el.addEventListener('focus', open);
    el.addEventListener('click', open);
    el.addEventListener('mouseleave', card.scheduleHide);
    el.addEventListener('blur', card.scheduleHide);
    // Make non-interactive mentions (span / li / td) keyboard-reachable so
    // the card is not mouse-only.
    if (!/^(A|BUTTON)$/.test(el.tagName) && !el.hasAttribute('tabindex')) {
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'button');
    }
  }

  fetch('data/bios.json', { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
    .then((bios) => {
      const byKey = new Map();
      for (const m of (bios && bios.members) || []) {
        if (!m) continue;
        const add = (nm) => { const k = nameKey(nm); if (k && !byKey.has(k)) byKey.set(k, m); };
        add(m.name);
        (m.name_aliases || []).forEach(add);
      }
      if (!byKey.size) return;

      // 1) Explicitly marked mentions, on any page. Skip the leadership cards
      //    (they render the person already) and anything inside a block that
      //    owns its own member links.
      document.querySelectorAll('[data-person]').forEach((el) => {
        if (el.closest('.mc-card, .member-card, .essc-member-card, .essc-programme, #members-grid')) return;
        const authored = String(el.getAttribute('data-person') || '')
          .replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '').trim();
        const m = byKey.get(nameKey(el.getAttribute('data-person')));
        if (!m) return;
        const href = el.tagName === 'A' ? el.getAttribute('href') : null;
        // Match the name as the page actually wrote it (the data-person value)
        // first, then the directory display names: the two can differ (an
        // initial dropped, a different honorific), and we want to wrap exactly
        // the visible name, not an affiliation line in the same <li>. Fall back
        // to wiring the whole element if no name text is found.
        const names = [authored, ...displayNames(m)]
          .filter((v) => v && nameKey(v))
          .filter((v, i, a) => a.indexOf(v) === i)
          .sort((a, b) => b.length - a.length);
        if (!wrapNameIn(el, m, names, href)) wire(el, m, href);
      });

      // 2) Auto-scan <main> prose for unmarked full-name mentions, so a name
      //    written in a paragraph cards itself without being hand-tagged, and
      //    keeps doing so as the directory grows. Full first+last only, on a
      //    word boundary, longest names first; each match becomes a wrapped
      //    span. Conservative by construction: a bare first name or surname
      //    never matches, and the SKIP_CLOSEST list keeps it out of chrome,
      //    links, forms, code, and the directory / programme blocks.
      const main = document.querySelector('main');
      if (!main) return;
      const names = [];
      const keyByName = new Map();
      for (const m of (bios.members || [])) {
        for (const disp of displayNames(m)) {
          if (!keyByName.has(disp.toLowerCase())) {
            names.push(disp);
            keyByName.set(disp.toLowerCase(), m);
          }
        }
      }
      if (!names.length) return;
      names.sort((a, b) => b.length - a.length);
      const re = new RegExp('(?<![\\p{L}])(' + names.map(escRe).join('|') + ')(?![\\p{L}])', 'u');

      const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
          if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          if (node.parentElement && node.parentElement.closest(SKIP_CLOSEST)) {
            return NodeFilter.FILTER_REJECT;
          }
          return re.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        },
      });
      const targets = [];
      for (let n = walker.nextNode(); n; n = walker.nextNode()) targets.push(n);
      const reG = new RegExp(re.source, 'gu');
      targets.forEach((node) => {
        const text = node.nodeValue;
        reG.lastIndex = 0;
        let last = 0, match, frag = null;
        while ((match = reG.exec(text))) {
          const m = keyByName.get(match[1].toLowerCase());
          if (!m) continue;
          frag = frag || document.createDocumentFragment();
          if (match.index > last) frag.appendChild(document.createTextNode(text.slice(last, match.index)));
          const span = document.createElement('span');
          span.textContent = match[1];
          wire(span, m);
          frag.appendChild(span);
          last = match.index + match[1].length;
        }
        if (frag) {
          if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
          node.parentNode.replaceChild(frag, node);
        }
      });
    })
    .catch(() => { /* silent: plain text stays a correct fallback */ });
})();

/* ── ECS³ faculty roster: self-healing headshots from the directory ────
   Every faculty card renders a monogram avatar from static markup, so the
   roster is complete with no JavaScript and no network. On load this matches
   each card's name against the NetSec directory (data/bios.json) by a
   normalised first|last key (titles and nobiliary particles stripped, the
   same scheme the ESSC programme uses to link speakers). When a name
   resolves, the card gains that person's live headshot and a link through to
   their profile. Nothing is hand-tagged: a scholar who is not in the
   directory today simply keeps the monogram, and starts showing a photo the
   first time they appear in the directory, with no edit to this page. A
   failed fetch or an unresolved name leaves the monogram untouched. */
(function () {
  const cards = Array.from(document.querySelectorAll('.ecs-faculty-card'));
  if (!cards.length) return;

  // Postnominals and nobiliary/patronymic particles dropped before keying,
  // so "Dr Silvia D'Amato" and "Silvia D'Amato" resolve to the same key.
  const POSTNOMINALS = new Set(['phd', 'jr', 'sr', 'ii', 'iii', 'iv', 'esq']);
  const PARTICLES = new Set([
    'de', 'del', 'della', 'di', 'da', 'das', 'dos',
    'van', 'von', 'vom', 'der', 'den', 'ter', 'ten',
    'la', 'le', 'el', 'al', 'ibn', 'bin', 'bint', 'zu', 'auf', 'af',
  ]);
  function nameKey(name) {
    if (!name) return null;
    let s = name.normalize('NFKD').replace(/[̀-ͯ]/g, '');
    s = s.replace(/^(Dr|Prof|Mr|Mrs|Ms|Mx)\.?\s+/i, '');
    s = s.replace(/[‘’ʼ'`]/g, '');
    const tokens = s.split(/[^A-Za-z]+/).filter(Boolean).map((t) => t.toLowerCase());
    const real = tokens.filter((t) => !POSTNOMINALS.has(t) && !PARTICLES.has(t));
    if (real.length < 2) return null;
    return real[0] + '|' + real[real.length - 1];
  }

  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const peopleUrl = lang === 'fr' ? 'people.fr.html' : lang === 'de' ? 'people.de.html' : 'people.html';
  const T = (s) => (window.netsecT && window.netsecT(s)) || s;

  fetch('data/bios.json', { cache: 'no-cache' })
    .then((r) => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)))
    .then((bios) => {
      const byKey = new Map();
      const add = (rawName, m) => {
        const k = nameKey(rawName);
        if (k && m && m.id && !byKey.has(k)) byKey.set(k, m);
      };
      for (const m of (bios && bios.members) || []) {
        add(m.name, m);
        for (const alias of (m.name_aliases || [])) add(alias, m);
      }
      for (const card of cards) {
        const nameEl = card.querySelector('.ecs-faculty-card-name');
        const m = nameEl && byKey.get(nameKey(nameEl.textContent));
        if (!m) continue;                       // not in the directory yet → keep monogram
        const avatar = card.querySelector('.mc-avatar');
        if (avatar && m.photo) {
          avatar.classList.remove('mc-avatar--initials');
          avatar.textContent = '';
          const img = document.createElement('img');
          img.src = m.photo; img.alt = ''; img.loading = 'lazy'; img.decoding = 'async';
          const webp = window.netsecWebp && window.netsecWebp(m.photo);
          if (webp) {
            const pic = document.createElement('picture');
            const src = document.createElement('source');
            src.type = 'image/webp'; src.srcset = webp;
            pic.appendChild(src); pic.appendChild(img);
            avatar.appendChild(pic);
          } else {
            avatar.appendChild(img);
          }
        }
        if (!card.querySelector('.ecs-faculty-card-link')) {
          const a = document.createElement('a');
          a.className = 'ecs-faculty-card-link';
          a.href = peopleUrl + '#' + m.id;
          a.textContent = T('View profile');
          card.appendChild(a);
        }
      }
    })
    .catch((err) => { console.warn('ecs-faculty: bios.json fetch failed; monograms kept:', err); });
})();

/* Audiences side-drawer — the recurring "Start where you are" role-router.
   ──────────────────────────────────────────────────────────────────────
   The homepage carries an inline #audiences section; this makes the same
   role-router available site-wide as a right-edge tab that opens a drawer.
   Reads /data/audiences.json, picks the locale off <html lang>, injects a
   fixed edge tab + a native <dialog> on every page. Native <dialog> gives
   Esc-to-close, focus trapping, and a ::backdrop for free.

   Z-order note: the tab/drawer sit below the Directory member-preview panel
   (z-index:120) on purpose, so on people.html the member preview wins the
   right edge and covers the tab while open, then the tab returns on close.
   Silent no-op if the JSON is missing or a locale block is absent. */
(function () {
  var ICONS = {
    researcher: '<path d="M6 18h8"/><path d="M3 22h18"/><path d="M14 22a7 7 0 1 0 0-14h-1"/><path d="M9 14h2"/><path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"/><path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>',
    policy: '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    member: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>',
    press: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>'
  };
  var SVG_OPEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';

  // The tab/drawer are a secondary wayfinding aid, not needed at first
  // paint, so the fetch + injection are deferred to idle time to keep
  // them off the critical load path (they were nudging about.html below
  // the Lighthouse performance budget). Default caching is fine — the
  // router content is stable, unlike the freshness-sensitive banner.
  function boot() {
    fetch('/data/audiences.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
        var block = data[lang] || data.en;
        if (!block || !block.cards || !block.cards.length) return;
        render(block);
      })
      .catch(function () { /* 404 or parse error — silent no-op */ });
  }
  if ('requestIdleCallback' in window) {
    requestIdleCallback(boot, { timeout: 2000 });
  } else {
    setTimeout(boot, 1200);
  }

  function icon(key) {
    return SVG_OPEN + (ICONS[key] || '') + '</svg>';
  }

  function render(block) {
    var tab = document.createElement('button');
    tab.type = 'button';
    tab.className = 'aud-tab';
    tab.setAttribute('aria-haspopup', 'dialog');
    tab.innerHTML =
      '<span class="aud-tab-icon" aria-hidden="true">' +
      SVG_OPEN + '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg></span>' +
      '<span class="aud-tab-label">' + esc(block.tab) + '</span>';

    var dlg = document.createElement('dialog');
    dlg.className = 'aud-drawer';
    dlg.setAttribute('aria-label', block.title);

    var cards = block.cards.map(function (c) {
      var links = (c.links || []).map(function (l) {
        var ext = l.external ? ' target="_blank" rel="noopener"' : '';
        var glyph = l.external
          ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>'
          : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';
        return '<a href="' + esc(l.href) + '"' + ext + '>' + esc(l.label) + ' ' + glyph + '</a>';
      }).join('');
      return '<div class="audience-card glass">' +
        '<h3><span class="aud-card-icon" aria-hidden="true">' + icon(c.icon) + '</span>' + esc(c.h3) + '</h3>' +
        '<p>' + esc(c.p) + '</p>' +
        '<div class="audience-links">' + links + '</div></div>';
    }).join('');

    dlg.innerHTML =
      '<div class="aud-head">' +
        '<div><span class="aud-eyebrow">' + esc(block.tab) + '</span>' +
        '<span class="aud-title">' + esc(block.title) + '</span></div>' +
        '<button type="button" class="aud-close" aria-label="' + esc(block.close || 'Close') + '">' +
        SVG_OPEN + '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>' +
      '</div>' +
      '<div class="aud-cards">' + cards + '</div>';

    document.body.appendChild(tab);
    document.body.appendChild(dlg);

    function openDrawer() {
      if (typeof dlg.showModal === 'function') { dlg.showModal(); } else { dlg.setAttribute('open', ''); }
      requestAnimationFrame(function () { dlg.classList.add('aud-open'); });
    }
    function closeDrawer() {
      dlg.classList.remove('aud-open');
      // Keep the dialog displayed through the slide-out, then close.
      // Timeout (not transitionend) so reduced-motion — where there is
      // no transition to fire — still closes reliably.
      window.setTimeout(function () {
        if (typeof dlg.close === 'function') { dlg.close(); } else { dlg.removeAttribute('open'); }
      }, 260);
    }

    tab.addEventListener('click', openDrawer);
    dlg.querySelector('.aud-close').addEventListener('click', closeDrawer);
    // Click on the ::backdrop registers as a click on the dialog itself.
    dlg.addEventListener('click', function (e) { if (e.target === dlg) closeDrawer(); });
    // Native Esc fires 'cancel'; intercept so the slide-out animates.
    dlg.addEventListener('cancel', function (e) { e.preventDefault(); closeDrawer(); });
    // A card link was followed — close so the drawer isn't left open behind
    // the destination (same-page anchors don't reload).
    dlg.querySelector('.aud-cards').addEventListener('click', function (e) {
      if (e.target.closest('a')) closeDrawer();
    });
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
})();

/* ═══════════════════════════════════════════════════════════════════
   Cinematic homepage: hero constellation, card tilt, faces marquee.
   Three independent presentational IIFEs, each a silent no-op when its
   hook element is absent, so they add nothing on pages that do not carry
   the markup. Colours track the live theme via the .dark class on the
   document element. Every loop pauses off-screen and when the tab is
   hidden. Reduced motion is honoured per feature.
   ═══════════════════════════════════════════════════════════════════ */

/* ── A. Hero network constellation (data-hero-net) ──────────────────
   A canvas of drifting nodes joined by proximity lines, with the odd
   bright pulse travelling an edge and a gentle pointer parallax. The
   node layout is a fixed hand-picked seed loosely evoking Europe,
   denser toward the centre-west, so it never clusters badly at load.
   Under reduced motion it paints a single static frame and stops. */
(function () {
  var canvas = document.querySelector('[data-hero-net]');
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext('2d');
  var hero = canvas.closest('.hero') || canvas.parentElement;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Fixed normalised seed coordinates (0..1). Hand-picked to sit denser
  // in the centre-west and thin out toward the east and north, so the
  // field reads as a loose map rather than an even grid. 40 nodes.
  var SEED = [
    [0.30, 0.34], [0.34, 0.30], [0.38, 0.38], [0.33, 0.44], [0.28, 0.40],
    [0.42, 0.32], [0.40, 0.46], [0.36, 0.52], [0.30, 0.52], [0.44, 0.40],
    [0.47, 0.36], [0.46, 0.50], [0.50, 0.44], [0.52, 0.34], [0.38, 0.60],
    [0.32, 0.62], [0.44, 0.62], [0.50, 0.58], [0.56, 0.48], [0.55, 0.40],
    [0.60, 0.42], [0.58, 0.56], [0.62, 0.36], [0.64, 0.50], [0.26, 0.30],
    [0.24, 0.46], [0.28, 0.56], [0.36, 0.24], [0.48, 0.26], [0.42, 0.54],
    [0.68, 0.44], [0.70, 0.34], [0.66, 0.58], [0.72, 0.50], [0.78, 0.40],
    [0.54, 0.64], [0.60, 0.62], [0.34, 0.68], [0.46, 0.70], [0.24, 0.62]
  ];

  var nodes = SEED.map(function (p, i) {
    return {
      bx: p[0], by: p[1],           // base normalised position
      phase: (i * 1.7) % (Math.PI * 2),
      speed: 0.5 + (i % 5) * 0.12,
      ampx: 4 + (i % 3) * 2,
      ampy: 3 + (i % 4) * 2,
      x: 0, y: 0
    };
  });

  var W = 0, H = 0, dpr = 1;
  var pointer = { tx: 0, ty: 0, x: 0, y: 0 };   // parallax offset, eased
  var pulses = [];
  var lastPulse = 0;
  var LINK = 0.16;   // link distance as a fraction of the min dimension
  var running = false;
  var visible = true;
  var rafId = 0;

  function palette() {
    var dark = document.documentElement.classList.contains('dark');
    return dark
      ? { node: 'rgba(150,185,255,', line: 'rgba(130,170,255,', pulse: 'rgba(190,215,255,' }
      : { node: 'rgba(0,51,153,',    line: 'rgba(10,90,200,',   pulse: 'rgba(10,132,255,' };
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = hero.clientWidth;
    H = hero.clientHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function positions(t) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var driftX = reduce ? 0 : Math.sin(t * 0.0004 * n.speed + n.phase) * n.ampx;
      var driftY = reduce ? 0 : Math.cos(t * 0.0004 * n.speed + n.phase) * n.ampy;
      n.x = n.bx * W + driftX + pointer.x;
      n.y = n.by * H + driftY + pointer.y;
    }
  }

  function draw(t) {
    var pal = palette();
    var linkDist = Math.min(W, H) * LINK;
    ctx.clearRect(0, 0, W, H);

    // Proximity lines, alpha falling off with distance.
    ctx.lineWidth = 1;
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var dx = nodes[i].x - nodes[j].x;
        var dy = nodes[i].y - nodes[j].y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < linkDist) {
          var a = (1 - d / linkDist) * 0.28;
          ctx.strokeStyle = pal.line + a.toFixed(3) + ')';
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }

    // Nodes.
    for (var k = 0; k < nodes.length; k++) {
      ctx.fillStyle = pal.node + '0.55)';
      ctx.beginPath();
      ctx.arc(nodes[k].x, nodes[k].y, 2, 0, Math.PI * 2);
      ctx.fill();
    }

    // Signal pulses travelling along an edge.
    if (!reduce) {
      for (var p = pulses.length - 1; p >= 0; p--) {
        var pu = pulses[p];
        pu.t += 0.02;
        if (pu.t >= 1) { pulses.splice(p, 1); continue; }
        var a2 = nodes[pu.a], b2 = nodes[pu.b];
        if (!a2 || !b2) { pulses.splice(p, 1); continue; }
        var px = a2.x + (b2.x - a2.x) * pu.t;
        var py = a2.y + (b2.y - a2.y) * pu.t;
        var fade = Math.sin(pu.t * Math.PI);
        ctx.fillStyle = pal.pulse + (0.9 * fade).toFixed(3) + ')';
        ctx.beginPath();
        ctx.arc(px, py, 2.6, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function spawnPulse() {
    // Pick a random pair that is currently within link distance.
    var linkDist = Math.min(W, H) * LINK;
    var candidates = [];
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var dx = nodes[i].x - nodes[j].x;
        var dy = nodes[i].y - nodes[j].y;
        if (Math.sqrt(dx * dx + dy * dy) < linkDist) candidates.push([i, j]);
      }
    }
    if (!candidates.length) return;
    var pick = candidates[Math.floor(Math.random() * candidates.length)];
    pulses.push({ a: pick[0], b: pick[1], t: 0 });
  }

  function frame(t) {
    // Ease the parallax toward the target offset.
    pointer.x += (pointer.tx - pointer.x) * 0.06;
    pointer.y += (pointer.ty - pointer.y) * 0.06;
    positions(t);
    draw(t);
    if (!reduce && t - lastPulse > 2600 && Math.random() < 0.4) {
      spawnPulse();
      lastPulse = t;
    }
    rafId = window.requestAnimationFrame(frame);
  }

  function start() {
    if (running || reduce) return;
    running = true;
    rafId = window.requestAnimationFrame(frame);
  }
  function stop() {
    running = false;
    if (rafId) window.cancelAnimationFrame(rafId);
    rafId = 0;
  }

  // Static single frame for the reduced-motion path.
  function paintStatic() {
    resize();
    positions(0);
    draw(0);
  }

  resize();
  window.addEventListener('resize', function () {
    resize();
    if (reduce) paintStatic();
  });

  if (reduce) {
    paintStatic();
    return;
  }

  // Pointer parallax, capped at ~8px.
  hero.addEventListener('pointermove', function (e) {
    var r = hero.getBoundingClientRect();
    var nx = (e.clientX - r.left) / r.width - 0.5;
    var ny = (e.clientY - r.top) / r.height - 0.5;
    pointer.tx = nx * 8;
    pointer.ty = ny * 8;
  });
  hero.addEventListener('pointerleave', function () { pointer.tx = 0; pointer.ty = 0; });

  // Pause when the hero scrolls out of view.
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible && !document.hidden) start(); else stop();
    }, { threshold: 0 });
    io.observe(hero);
  } else {
    start();
  }
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stop();
    else if (visible) start();
  });

  start();
})();

/* ── D. Card tilt, glare and border trace (data-tilt) ───────────────
   One delegated pointer handler for every [data-tilt] card. It sets the
   rotation (--tx / --ty, capped at 3 degrees) and the glare centre
   (--mx / --my) as inline custom properties, then eases them back to
   rest on leave. Skipped entirely on touch pointers and under reduced
   motion, so nothing binds where the effect does not belong. */
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
  if (reduce || coarse) return;
  if (!document.querySelector('[data-tilt]')) return;

  var MAX = 3;   // maximum tilt in degrees

  function onMove(e) {
    var card = e.target.closest('[data-tilt]');
    if (!card) return;
    var r = card.getBoundingClientRect();
    var px = (e.clientX - r.left) / r.width;    // 0..1
    var py = (e.clientY - r.top) / r.height;    // 0..1
    // rotateX tips on the vertical axis, rotateY on the horizontal.
    card.style.setProperty('--ty', ((px - 0.5) * 2 * MAX).toFixed(2) + 'deg');
    card.style.setProperty('--tx', ((0.5 - py) * 2 * MAX).toFixed(2) + 'deg');
    card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
    card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
  }

  function onLeave(e) {
    var card = e.target.closest('[data-tilt]');
    if (!card) return;
    card.style.setProperty('--tx', '0deg');
    card.style.setProperty('--ty', '0deg');
  }

  // Delegated on document so cards rendered after load (the home News
  // list is rebuilt from JSON) still respond without re-binding.
  document.addEventListener('pointermove', onMove);
  document.addEventListener('pointerout', onLeave);
})();

/* ── E. Faces marquee (data-faces-marquee) ──────────────────────────
   Builds one scrolling row of circular headshots from the members that
   carry a photo, then duplicates the row so the CSS -50% loop is
   seamless. Purely decorative: the container is aria-hidden and every
   image has an empty alt. Silent no-op if the fetch fails, matching the
   site's other data-driven blocks. */
(function () {
  var box = document.querySelector('[data-faces-marquee]');
  if (!box) return;

  fetch('data/bios.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (!data) return;
      var members = Array.isArray(data.members) ? data.members : [];
      var withPhoto = members.filter(function (m) { return m && m.photo; });
      if (!withPhoto.length) return;
      render(withPhoto);
    })
    .catch(function () { /* JSON 404 or parse error — silent no-op */ });

  function render(list) {
    var track = document.createElement('div');
    track.className = 'faces-track';
    // Two identical halves for the seamless -50% loop.
    appendRow(track, list);
    appendRow(track, list);
    box.appendChild(track);
  }

  function appendRow(track, list) {
    list.forEach(function (m) {
      var pic = document.createElement('picture');
      var webp = window.netsecWebp ? window.netsecWebp(m.photo) : null;
      if (webp) {
        var src = document.createElement('source');
        src.type = 'image/webp';
        src.srcset = webp;
        pic.appendChild(src);
      }
      var img = document.createElement('img');
      img.src = m.photo;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      img.width = 60;
      img.height = 60;
      pic.appendChild(img);
      track.appendChild(pic);
    });
  }
})();
