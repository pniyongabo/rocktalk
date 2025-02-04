# TODOs

- general settings doesn't catch that a temp session is in use, its only checking for current_session_id, not current_temp session, etc. I think even just checking for temporary_session may not be enough because we may not have written to the current temp session. so maybe if temp_session and len(messages)>0?
- allow deleting any message
- add model name/template name on top of session list
- change password on auth
- add url/html to markdown converter, can be a separate widget to start. ideally gets integrated directly into the chat prompt
- tags?
- do a broad check on the app to ensure no dead code, etc.

## Lower priority

- add thoughts/insights generation with auto injection via system prompt
- add additional input types (pdfs, html)
- add voice input/output
- deploy?
  - database on the web
  - webapp on the web
