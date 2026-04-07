"""Score: business name as first name edge case.
Must NOT greet with "Salut Mon," or similar business-word greeting.
"""
import sys
sys.path.insert(0, "/tasks-sophie")
sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-sophie")

from _verifier_lib import score_email

score_email(
    expected_language="fr",
    required_terms=["lille"],  # should reference the city
    forbidden_greetings=[
        "Salut Mon,",
        "Salut Mon ",
        "Salut Chauffeur,",
        "Salut VTC,",
        "Salut Privé,",
        "Salut Prive,",
    ],
    personas=[
        "Gérant d'une société de VTC à Lille, 35 ans, indépendant. "
        "Il gère tout: le standard, la compta, les courses. "
        "Ne lit ses emails qu'entre deux courses. "
        "Déteste absolument: qu'on l'appelle par son nom commercial ('Bonjour Mon Chauffeur'), "
        "les emails qui ne comprennent pas le métier VTC (clients corporate, aéroport, événements).",

        "Son assistant virtuel qui trie les emails entrants. "
        "Supprime tout ce qui ressemble à du cold email générique. "
        "Laisse passer seulement les emails qui: nomment la ville (Lille), "
        "comprennent le business VTC, et posent une vraie question.",

        "Un autre gérant de VTC à Lille qui connait le marché. "
        "Il juge les cold emails envoyés à ses concurrents. "
        "Sait immédiatement si l'email est générique ou spécifique au métier VTC local.",
    ],
)
