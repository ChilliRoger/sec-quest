# Vibe Coding Rules
 
> A practical guide to building effectively with AI coding tools like Cursor, Claude, and Gemini.
 
---
 
## 1. Define Your Vision Clearly
 
Start with a strong, detailed vision of what you want to build and how it should work. If your input is vague or messy, the output will be too. Remember: **garbage in, garbage out.**
 
Take time to think through your idea from both a product and user perspective. Use tools like **Gemini 2.5 Pro** in Google AI Studio to help structure your thoughts, outline the product goals, and map out how to bring your vision to life. The clearer your plan, the smoother the execution.
 
---
 
## 2. Plan Your UI/UX First
 
Before you start building, take time to carefully plan your UI. Use tools like **v0** to help you visualize and experiment with layouts early.
 
- Consistency is key — decide on your design system upfront and stick with it.
- Create reusable components (buttons, loading indicators, etc.) right from the start.
- Check out **[21st.dev](https://21st.dev/)** — it has a ton of components with their AI prompts; just copy-paste the prompt.
 
---
 
## 3. Master Git & GitHub
 
Git is your best friend. You **must** know GitHub and Git — it will save you a lot if AI messes things up, since you can easily return to an older version.
 
- After finishing a big feature, always commit your code.
- Without Git, your codebase could be destroyed with some wrong changes.
- It makes everything much easier and organized.
 
---
 
## 4. Choose a Popular Tech Stack
 
Stick to widely-used, well-documented technologies. AI models are trained on public data — the more common the stack, the better the AI can help you write high-quality code.
 
**Recommended stack:**
 
| Layer | Tool |
|---|---|
| Frontend & APIs | Next.js |
| Database & Auth | Supabase |
| Styling | Tailwind CSS |
| Hosting | Vercel |
 
This combo is beginner-friendly, fast to develop with, and removes a lot of boilerplate and manual setup.
 
---
 
## 5. Utilize Cursor Rules
 
Cursor Rules is your friend. You must have very good Cursor Rules covering:
 
- Your full tech stack
- Instructions for the AI model
- Best practices and patterns
- Things to avoid
 
Find a ton of templates at **[cursor.directory](https://cursor.directory/)**.
 
---
 
## 6. Maintain an Instructions Folder
 
Always have an `instructions/` folder containing markdown files. It should be full of:
 
- Docs and example components to guide the AI
- Context files for your project architecture
 
> Alternatively, use **Context7 MCP** — it has tons of documentation built in.
 
---
 
## 7. Craft Detailed Prompts
 
Now the building phase starts. Again, **garbage in, garbage out.** You must give very good prompts.
 
If you're struggling to write a good prompt, use **Gemini 2.5 Pro** in Google AI Studio to generate a detailed, intricate version of it. Your prompt should be as detailed as possible — do not leave any room for the AI to guess.
 
---
 
## 8. Break Down Complex Features
 
Do **not** give huge prompts like *"build me this whole feature."* The AI will hallucinate and produce poor output.
 
Break down any complex feature into phases:
 
- Aim for **3–5 smaller requests** per feature, or more depending on complexity.
- Each prompt should focus on one specific piece of the feature.
 
---
 
## 9. Manage Chat Context Wisely
 
When the chat gets very long, **open a new one.** The AI context window is limited — if the chat is too big, it will forget earlier patterns and design decisions and start producing bad outputs.
 
When starting a new chat window:
 
- Give a brief description of the feature you were working on.
- Mention the specific files involved.
 
---
 
## 10. Don't Hesitate to Restart / Refine Prompts
 
When the AI goes in the wrong direction or adds things you didn't want, **go back, refine the prompt, and send again.** This is much better than continuing with bad code, since the AI will try to patch its mistakes and likely introduce new ones.
 
---
 
## 11. Provide Precise Context
 
Providing the right context is the most important thing, especially as your codebase grows.
 
- Mention the specific files where changes will be made.
- Make sure referenced files are actually relevant — too much context can overwhelm the AI too.
- Always provide the right components that give the AI the context it needs.
 
---
 
## 12. Leverage Existing Components for Consistency
 
A great trick: mention previously built components when building new ones. The AI will quickly pick up your patterns and apply them to new components without much extra effort.
 
---
 
## 13. Iteratively Review Code with AI
 
After building each feature:
 
1. Copy the full feature code and paste it into **Gemini 2.5 Pro** (Google AI Studio).
2. Ask Gemini to act as a **security expert** and spot any flaws.
3. In a separate chat, ask it to act as a **performance expert** and identify bad coding patterns.
4. Take Gemini's insights back into **Claude in Cursor** and fix the flagged issues.
5. Repeat until Gemini confirms everything is clean.
 
Gemini's large context window makes it great at spotting issues across entire features.
 
---
 
## 14. Prioritize Security Best Practices
 
Security is critical. Always follow these patterns:
 
| Vulnerability | Fix |
|---|---|
| **Trusting client data** — using form/URL input directly | Always validate & sanitize on the server; escape output |
| **Secrets in frontend** — API keys in React/Next.js client code | Keep secrets server-side only (env vars); ensure `.env` is in `.gitignore` |
| **Weak authorization** — only checking if logged in, not if allowed | Server must verify permissions for every action & resource |
| **Leaky errors** — showing stack traces/DB errors to users | Generic error messages for users; detailed logs for devs |
| **No ownership checks (IDOR)** — letting user X access user Y's data | Server must confirm the current user owns/can access the resource |
| **Ignoring DB-level security** — bypassing RLS and other DB features | Define data access rules directly in your database (e.g., RLS) |
| **Unprotected APIs & sensitive data** — missing rate limits or unencrypted data | Rate limit APIs (middleware); encrypt sensitive data at rest; always use HTTPS |
 
> No website is 100% secure, but following these patterns eliminates the most critical vulnerabilities.
 
---
 
## 15. Handle Errors Effectively
 
When you face an error, you have two options:
 
1. **Revert and retry** — go back and prompt the AI again. This often works.
2. **Continue forward** — copy-paste the error from the console and ask the AI to fix it.
 
> If the AI hasn't solved the error after **3 requests**, revert, refine your prompt, and start fresh with the correct context.
 
---
 
## 16. Debug Stubborn Errors Systematically
 
If an error persists after 3+ attempts and the AI is going in circles:
 
1. Tell Claude to **take an overview** of the components the error is coming from.
2. Ask it to **list the top suspects** it thinks are causing the error.
3. Tell it to **add logs** to those areas.
4. **Provide the log output** back to the AI.
 
This approach significantly helps the AI pinpoint the real problem.
 
---
 
## 17. Be Explicit: Prevent Unwanted AI Changes
 
Claude has a tendency to add, remove, or modify things you didn't ask for. A simple instruction at the end of every prompt works very well:
 
> *"Do not change anything I did not ask for. Only do exactly what I told you."*
 
It's blunt, but it's effective.
 
---
 
## 18. Keep a "Common AI Mistakes" File
 
Maintain a file documenting mistakes you notice Claude making repeatedly. Add all of them to that file and reference it when adding new features.
 
This prevents the AI from making the same frustrating repeated mistakes and saves you from repeating yourself every session.
 
---