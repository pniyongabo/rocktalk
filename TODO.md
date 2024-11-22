# TODOs

- add model settings options
  - store in session settings, but also allow global setting? perhaps link to same dialog from both? or just set a default and allow individual session to override. add print debug logging to confirm the choices are going through. Also if a user modifies a predefined prompt setting, auto switch the classification to "custom"
  - should logic like load_or_create_session be moved from chat.py to ChatSession? Similar for message saving or session updating logic. Perhaps better to store at the data layer so chat has fewer things to worry about? Define an api for Session and Message so that Chat can just receive and not worry about underlying implementation? Session and Message will need to interact directly with storage. This may allow easier optimization since we can isolate the slow steps of reading/writing storage and loading message state into session_state.
- do a broad check on the app to ensure no dead code, etc.
- make sure storage protocol and implementation are consistent

## Lower priority

- add system prompt (e.g. "Prefer markdown formatting for responses").. Currently working but need to pass a SystemMessageinto messages which may require some reworking? can we insert more than one systemMessage?
  - add thoughts/insights generation with auto injection via system prompt
- stop option to cancel the stream
- add additional input types (pdfs, html)
- add voice input/output
- deploy?
  - database on the web
  - webapp on the web
