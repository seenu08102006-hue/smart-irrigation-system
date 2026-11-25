# Deployment

The production build is a **single Flask process** that serves both the API and the compiled React app. It needs no seed data and
no pre-trained model: models are trained from whatever users upload.

## Before deploying (all platforms)
```bash
cd frontend && npm install && npm run build      # compiles into backend/static
```
Optional environment variables:

| Variable | Meaning |
|---|---|
| `DATABASE_PATH` | SQLite file (put it on a persistent disk) |
| `UPLOAD_DIR` | where uploaded files are stored (default `uploads/`) |
| `USER_MODEL_DIR` | where the SVMs trained on uploads are stored (default `user_models/`) |
| `PORT` | port for `python backend/app.py` |

The upload limit is 25 MB (`MAX_UPLOAD_MB` in `backend/config.py`). Behind Nginx also set `client_max_body_size 25m;`.

## A. Linux VPS (Ubuntu) with Gunicorn + Nginx
```bash
sudo apt install python3-venv nginx
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 app:app
```
Nginx: `location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }`, then `certbot --nginx` for HTTPS.
Run Gunicorn under `systemd` so it restarts automatically.

**Use one worker with threads.** The analysis runs in a background thread of the web process and its progress is kept in memory,
so the progress bar only works when all requests reach the same process. For several workers, move the analysis to a task queue
(RQ/Celery) and store progress in the database.

## B. Windows
```bash
pip install -r backend/requirements.txt
cd backend
python -c "from waitress import serve; import app; serve(app.app, host='0.0.0.0', port=5000)"
```

## C. Render / Railway (PaaS)
* Build: `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build`
* Start: `cd backend && gunicorn -w 1 --threads 8 app:app`
* Attach a **persistent disk** and point `DATABASE_PATH`, `UPLOAD_DIR` and `USER_MODEL_DIR` to it, otherwise uploads, models and
  history are wiped on every deploy.

## D. Docker
```dockerfile
FROM node:20 AS web
WORKDIR /app/frontend
COPY frontend/ .
RUN npm install && npm run build            # writes ../backend/static

FROM python:3.12-slim
WORKDIR /app
COPY . .
COPY --from=web /app/backend/static backend/static
RUN pip install -r backend/requirements.txt gunicorn
ENV PORT=8000
CMD ["sh", "-c", "cd backend && gunicorn -w 1 --threads 8 -b 0.0.0.0:8000 app:app"]
```

## Hardening checklist
* There is **no login**. Anyone who can open the site can upload, view and delete datasets: use a VPN, HTTP basic auth or add
  authentication before exposing it publicly.
* Serve over HTTPS, and restrict CORS origins in `backend/app.py` if the frontend is hosted on another domain.
* Uploaded files are real user data: back up `database/irrigation.db`, `uploads/` and `user_models/`, and delete datasets you no
  longer need (Datasets page).
