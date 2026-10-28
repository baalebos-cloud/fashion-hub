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


## Google Cloud Vertex AI express mode

Seam can use AI_PROVIDER=vertex_ai with Google Cloud Vertex AI **express
mode** instead of the previous n8n configuration. Set the following private
environment variables only on the Fashion Hub Railway backend service:

    AI_PROVIDER=vertex_ai
    AI_MODEL=gemini-3-flash-preview
    VERTEX_AI_API_KEY=<Google Cloud Vertex AI express-mode API key>

The provider uses the Google Vertex express-mode generateContent endpoint at
https://aiplatform.googleapis.com and the x-goog-api-key header.
It requires an express-mode API key; a Gemini API key from AI Studio and
a standard Google Cloud IAM service-account credential use different
authentication and cannot be substituted.

Never paste API keys into chat, the GitHub repository, or Vercel VITE_
variables. An n8n API_URL/API_KEY cannot authenticate to Google's API.
Keep AI_API_KEY for Anthropic if needed; Vertex uses VERTEX_AI_API_KEY.

Service-account/ADC-based Vertex AI on a standard GCP project is a different
setup not enabled by this express-mode adapter. To use standard Vertex AI,
add the supported Google Cloud authentication library and a dedicated
least-privileged IAM identity, then integrate its OAuth flow separately.

Seam still limits the model prompt to the signed-in role's app map and
cannot perform payments or order transitions. If the AI endpoint is down or
unconfigured, it gives fixed role-specific navigation hints and does not
show internal error messages to end users. Provider calls have bounded
output tokens and HTTP timeouts.
