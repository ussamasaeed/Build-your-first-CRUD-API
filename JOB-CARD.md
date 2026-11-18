# Job card

What it does (one sentence):
Classifies a task by category and priority
based on its title.

Input:
{ "text": "string, 1-2000 characters" }

Output:
{
  "category": one of [
    "work", "personal", "learning",
    "maintenance", "other"
  ],
  "priority": one of ["low", "normal", "high"],
  "confidence": 0.0-1.0,
  "reason": "one short sentence"
}

It must never:
Invent categories outside the allowed list,
add unexpected fields, or return arbitrary
text instead of the defined JSON.

When unsure it should:
Return category "other" with low confidence,
rather than guessing.