"""Score: English e-commerce candle brand, Shopify connected."""
import sys
sys.path.insert(0, "/tasks-sophie")
sys.path.insert(0, "/Users/eliott/Documents/GitHub/autoagent/tasks-sophie")

from _verifier_lib import score_email

score_email(
    expected_language="en",
    required_terms=["jamie"],  # should greet Jamie
    forbidden_greetings=[
        "Hey Wildheart,",
        "Hi Wildheart,",
        "Hey Candles,",
    ],
    personas=[
        "Jamie Rodriguez, 33, solo founder of a US candle e-commerce brand. "
        "Sells on Shopify. Has been burned by every SEO/content agency she tried. "
        "Gets 40+ cold emails per week from marketing agencies. "
        "Looks for: someone who actually understands the candle niche "
        "(gift market, scent trends, Shopify store economics), not generic e-commerce tropes.",

        "Jamie's best friend, who runs another small DTC brand. "
        "They forward each other cold emails to laugh at. "
        "The bar for 'actually useful' is very high. "
        "Respect signals: specificity, no AI slop, not pushing a demo in the first email.",

        "An e-commerce consultant who coaches small DTC brands. "
        "Reviews cold emails sent to his clients. "
        "Looks for: emails that understand Shopify-specific constraints, "
        "the realities of solo-founder operations, and don't waste their time.",
    ],
)
