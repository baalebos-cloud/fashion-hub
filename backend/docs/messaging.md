# Messaging

`Conversation` (scoped to an order, or general) + `Message`.

`MessagingService.get_or_create_conversation` finds an existing thread
between two participants for a given order before creating a new one, so
repeated "contact tailor" actions don't fragment into multiple threads.

`MessagingService.send_message` enforces that the sender is actually a
participant in the conversation before persisting — this is the
authorization boundary for the whole messaging feature.
