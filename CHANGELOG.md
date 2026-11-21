# Changelog

Notable changes to this project, newest first.

## 2026-11-19

### Performance

Server time spent on storage in each request went from about 135 ms to about 1–6 ms when the request reaches a running instance. Measured on Vercel with the new `Server-Timing` header:

- **The app runs next to the database.** `vercel.json` moves it from Washington, D.C. (`iad1`, Vercel's default) to Portland (`pdx1`), beside the Upstash database in Oregon. Each storage call went from about 58 ms to about 1 ms.
- **Connections to Redis are reused.** A shared pool of kept-alive HTTPS connections replaces a new connection per call, which cost extra round trips each time.
- **Fewer storage calls.** Loading a game that hasn't changed no longer saves it back, a new game is saved once instead of twice, and Play Again doesn't load the old game first. A reload is 1 call; a move is 2.
- **API handlers run in a thread pool**, so one request's storage calls don't hold up other requests on the same instance. Memory mode now stores copies of games too, so simultaneous requests for one game (like a double-click) can't corrupt it.

### Fixed

- **Blind order now follows heads-up rules.** The dealer posts the small blind and acts first before the flop. From the flop on, the big blind acts first and the dealer acts last. Previously the non-dealer posted the small blind and acted first on every street.
- **Hands no longer freeze when a player can't cover a blind or bet.** A player with fewer than 20 chips who posted a blind, called or went all-in for less than the bet was still asked to act, and the hand got stuck. Now the part of the other player's bet they can't match is returned and the remaining cards are dealt straight to a showdown. In a 300-game stress test the old code froze in 24 games; the fixed code finished all 900 games tested.
- **Deploy scripts can be run as documented.** `deploy/*.sh` and `src/main.py` weren't marked executable in git, so `sudo ./deploy/deploy-nginx.sh` failed with "permission denied" on a fresh clone.

### Added

- **Vercel deployment on the free Hobby plan.** Vercel spreads requests across short-lived instances that don't share memory, which made games reset at random. Now:
  - Games are stored in Upstash Redis when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` (or `KV_REST_API_URL` and `KV_REST_API_TOKEN`) are set. This uses Python's standard library, so there are no new dependencies. Idle games are deleted after 7 days.
  - Without those settings, games stay in memory as before, so local, Docker and Raspberry Pi setups work unchanged. On Vercel it logs a warning.
  - A root-level `app.py` gives Vercel an entrypoint that loads the real app from `src/web/app.py`.
- **Refreshing the web page resumes your game** instead of starting a new one.
- **Play Again button** (and `POST /api/new-game` endpoint) to start a new match once a player runs out of chips.
- **License:** released into the public domain under the Unlicense (`LICENSE`).
- This changelog.

### Changed

- All feature branches (`web-ui`, `ComposerBugFixes`, `nginx_deploy`) were merged into `main`, which is now the only branch.
- README rewritten to cover the web interface, Docker, Raspberry Pi, nginx HTTPS, Vercel, the game rules and the license.

## 2026-02-19 and earlier

- Web interface: a browser table served by FastAPI, sharing the game engine with the command line version.
- Docker and Docker Compose setup, a systemd service for Raspberry Pi, and an nginx HTTPS reverse proxy with self-signed certificates. The app moved from port 8000 to 3076, with HTTPS on 3077.
- Smarter AI betting: raises are capped at what the opponent can match, and the AI considers the opponent's stack.
- Improved raise input on the web page and clearer showdown output in the command line version.
- Initial release: heads-up Texas Hold'em against an AI opponent in the terminal.
