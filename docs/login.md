# Option 1

Command: Add login and logout with a public read-only view to the "Public" navigation

app.py 
- Added session import
- APP_USERNAME / APP_PASSWORD read from env vars (defaults: admin / changeme)
- before_request guard redirects unauthenticated requests to /login?next=<path> — public endpoints (public_*, login, logout, static) are exempt
- GET/POST /login — validates credentials, sets session["logged_in"], redirects to next or Upload on success 
- POST /logout — clears session, redirects to /public/organization 

base.html
- Logged-in: shows full admin nav + search bar + Logout button  
- Logged-out: shows only the Public nav link + Login button (no search bar) 
                                                                            
login.html — clean centered sign-in card with username/password fields; flashes invalid-credential errors via the existing flash message block 

To change credentials set env vars before starting the app: 
APP_USERNAME=myuser APP_PASSWORD=mypassword python app.py 

# Option 2

Command: Add login and logout based on a chanllenge word provided as an environment variable; otherwise just show the "Public" pages

app.py
- CHALLENGE_WORD = os.environ.get("CHALLENGE_WORD", "") — if the env var is not set, login will always fail (no back-door default)
- before_request guard redirects unauthenticated requests to /login; public endpoints are exempt
- POST /login — compares submitted word against CHALLENGE_WORD, sets session["logged_in"] on match
- POST /logout — clears session, redirects to Public

base.html
- Logged-out: only Public nav link + Login button (no search bar)
- Logged-in: full admin nav + search bar + Logout button

login.html — single password-style field labelled "Challenge Word"

To set the challenge word before starting the app:
CHALLENGE_WORD=mysecretword python app.py
