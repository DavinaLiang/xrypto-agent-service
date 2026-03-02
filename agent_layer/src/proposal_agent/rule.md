# Proposal and Comment Classification Rules

## CRITICAL CLASSIFICATION RULE

Treat the user's message as a **PROPOSAL** whenever it clearly suggests changing or adding anything in the structured plan (milestones or funding). This includes both small tweaks and big redesigns.

Examples that MUST be treated as PROPOSAL (not free_comment):
- "We should extend milestone 2 from 1 month to 3 months."
- "Reduce the scope of the first milestone and move some work to milestone 3."
- "Increase the tokens in the second funding stage from 1000 to 1500."
- "Add a new milestone just for community testing before launch."
- "Let's introduce an extra funding phase dedicated to marketing."

A **FREE COMMENT** is a general opinion, question, clarification request, or emotional statement that does **not** ask for a concrete change to milestones or funding.
Examples of FREE COMMENT:
- "I like this plan."
- "The team did a great job."
- "I'm not sure I understand the second stage."
- "Can you explain the funding breakdown?"

--- PROPOSAL TYPE CLASSIFICATION ---

1. milestone_update
    - Purpose: Modifying the details, duration, or scope of an **existing** milestone.
    - Typical intent:
       - Changing the time, scope, or content of a known milestone (by name or index).
       - Moving work from one milestone to another.
    - Examples:
       - "Change milestone 1 to focus only on backend work."
       - "Extend the deadline of milestone 3 by two weeks."
       - "Move UI design from milestone 2 into milestone 1."

2. fundingplan_update
    - Purpose: Modifying the allocation, amount, or schedule of **existing** funding plan entries/batches.
    - Typical intent:
       - Changing token amounts or percentages for current stages.
       - Moving or delaying the release time of funds.
    - Examples:
       - "Increase the second funding batch from 10% to 20%."
       - "Shift the release of the last funding stage to after milestone 4."
       - "Reallocate 500 tokens from the marketing stage to development."

3. add_milestone
    - Purpose: Suggesting the **addition** of a brand new, previously unlisted milestone or task.
    - Typical intent:
       - Inserting a new phase into the project timeline.
       - Creating a dedicated milestone for a specific activity.
    - Examples:
       - "Add a new milestone for external security audit."
       - "Let's introduce a separate milestone just for user research."
       - "We should have a post-launch monitoring milestone."

4. add_fundingplan
    - Purpose: Suggesting the **addition** of a new funding batch or source to the existing funding plan.
    - Typical intent:
       - Introducing a new funding stage or budget line.
       - Securing extra tokens for a specific purpose.
    - Examples:
       - "Add another funding round dedicated to marketing."
       - "We need an additional 2000 tokens for community incentives."
       - "Create a new funding stage before launch for audits."

--- COMMENT TYPE ---

1. free_comment: 
   - Purpose: General feedback.
   - Intent: Any statement that does not meet the criteria of an actionable proposal (e.g., 'I like this plan.', 'What is the team size?', 'Good work!').
