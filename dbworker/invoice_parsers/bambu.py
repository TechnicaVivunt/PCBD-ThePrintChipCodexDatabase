"""
Bambu Lab order-confirmation-email parser.

NOT YET IMPLEMENTED. Deliberately left as a stub rather than a guess:
this project has already spent real time twice building against an
assumed structure instead of a real sample (the Flight-chunk escaping
bug, and the original "rows" regex) and having to redo it once the
real thing showed up. An invoice email's exact HTML/text structure is
exactly this kind of thing -- easy to get subtly wrong from memory,
easy to get right from one real example.

To implement this: save a real Bambu Lab order confirmation as a raw
.eml file (or paste its raw HTML source), personal/payment details
redacted if you want, and this function gets built against that.

Expected return shape -- see invoice_parsers/__init__.py's docstring
for the full field list.
"""


def parse(raw_text_or_html):
    raise NotImplementedError(
        "Bambu Lab invoice parsing isn't built yet -- needs a real order "
        "confirmation email to build against. See this module's docstring."
    )
