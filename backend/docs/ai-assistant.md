# AI Assistant

## Scope

The assistant is a **navigation and support layer**, not a general-purpose
chatbot and not a system administrator — see
`app/integrations/ai/prompts.py::NAVIGATION_ASSISTANT_SYSTEM_PROMPT`. It
never executes financial actions or reveals another user's data; it only
tells the user where to go and what to do.

## Role-scoped app map

`app/integrations/ai/navigation_agent.py::ROLE_APP_MAP` is a static,
explicit mapping of page names to routes **per role**. The current user's
role-appropriate subset is injected into the system prompt before every
call — the model is never asked to infer routes from general knowledge,
which is what prevents incorrect navigation instructions (an explicit edge
case in the project spec). Expand `ROLE_APP_MAP` as new pages ship; do not
rely on the model to "know" the app's routes.

## Conversation persistence

`AIService` persists every turn (`AIConversation`, `AIMessage`) scoped to
`user_id`; a conversation can only be continued by the user who started
it (`AIService.send_message` checks `conversation.user_id == user_id`).

## Fashion assistant (style search)

`app/integrations/ai/fashion_assistant.py::extract_search_filters` turns a
free-text style request ("something floral for a summer wedding, under
$200") into structured filters (`garment_type`, `style_tags`, budget range)
for `search_service.py` — kept as a separate, narrower-scoped prompt from
the navigation assistant.

## Feedback loop

`AIAction.was_helpful` (boolean, nullable) lets the client report whether a
given suggestion actually helped, via `AINavigationService.record_feedback`
— use this to audit and improve `ROLE_APP_MAP`/prompts over time, directly
addressing the "AI gives an incorrect navigation instruction" edge case.
