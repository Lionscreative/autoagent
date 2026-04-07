"""Score: German forklift prospect. Must be ENTIRELY in German."""
import sys
sys.path.insert(0, "/tasks-sophie")
sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-sophie")

from _verifier_lib import score_email

score_email(
    expected_language="de",
    required_terms=["thomas"],  # should greet Thomas
    forbidden_greetings=[
        "Salut ",
        "Bonjour ",
        "Hi Thomas,",  # should be Hallo in German
    ],
    personas=[
        "Thomas Müller, 52 Jahre alt, Geschäftsführer eines Gabelstapler-Service in Hamburg. "
        "Pragmatisch, sachlich, wenig Geduld für Marketing-Floskeln. "
        "Erwartet: klare deutsche Sprache (keine englischen Begriffe wie 'Workflow' oder 'Content'), "
        "Verständnis der B2B-Logistik-Branche, konkrete Vorschläge statt Verkaufsgespräche.",

        "Die Sekretärin der MF Gabelstapler GmbH, die alle E-Mails filtert. "
        "Leitet nur weiter, was direkt relevant ist. "
        "Löscht sofort: englische Wörter in deutschen E-Mails, generische Werbung, "
        "alles was nach 'KI-generiert' aussieht.",

        "Ein Wettbewerber im Gabelstapler-Markt, der auch E-Mails von SEO-Agenturen erhält. "
        "Bewertet, ob die E-Mail den spezifischen Kontext der Gabelstapler-Branche "
        "(Wartung, Zertifizierungen, B2B-Kunden) versteht, oder ob es generischer Marketing-Müll ist.",
    ],
)
