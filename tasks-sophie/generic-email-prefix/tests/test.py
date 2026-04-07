"""Score: Generic support@ prefix. Must NOT greet with a bad name."""
import sys
sys.path.insert(0, "/tasks-sophie")
sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-sophie")

from _verifier_lib import score_email

score_email(
    expected_language="en",
    required_terms=["startup"],  # reference the business topic
    forbidden_greetings=[
        "Hey Support,",
        "Hi Support,",
        "Hey support,",
        "Hi support,",
    ],
    personas=[
        "Founder of an Asian startup consultancy, 40 years old. "
        "Receives 50+ cold emails per week from SEO agencies. "
        "Deletes anything that: uses 'Support' as a name, "
        "is obviously generic, doesn't understand the Asian startup market.",

        "VA (virtual assistant) filtering emails at support@. "
        "Forwards maybe 2% of cold emails to the founder. "
        "Looks for: specific mention of Asian market, real understanding of startup pain points, "
        "never forwards generic blast emails.",

        "A competing startup consultancy owner who reviews cold email samples. "
        "Can tell within 5 seconds whether an email is targeted or template. "
        "Values: concrete market insights, specificity to Asian startup context.",
    ],
)
