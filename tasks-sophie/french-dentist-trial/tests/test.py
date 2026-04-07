"""Score: French dentist trial day 4, nudge_complete_onboarding."""
import sys
sys.path.insert(0, "/tasks-sophie")
sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-sophie")

from _verifier_lib import score_email

score_email(
    expected_language="fr",
    required_terms=["marie"],  # should greet Marie
    forbidden_greetings=[
        "Salut Cabinet,",
        "Salut Dentaire,",
        "Salut Dupont,",  # should use first name, not last
    ],
    personas=[
        "Dentiste indépendante, 38 ans, cabinet à Paris 11, ouvert depuis 8 ans. "
        "Très occupée entre patients et admin. Mère de famille. "
        "Skeptique envers le marketing digital mais sait qu'il faut s'y mettre. "
        "Préfère les emails courts et directs, en français naturel.",

        "Office manager du cabinet Dupont, filtre les emails de Marie. "
        "Transmet moins de 10% des emails au médecin. "
        "Cherche: un vrai ROI, un argument spécifique à la dentisterie parisienne, "
        "pas du jargon SEO générique.",

        "Marie Dupont elle-même, qui lit ses emails entre deux patients à midi. "
        "Veut voir: du français naturel (pas traduit de l'anglais), "
        "une compréhension du métier dentaire (pas juste 'SEO'), "
        "une question à laquelle elle a envie de répondre.",
    ],
)
