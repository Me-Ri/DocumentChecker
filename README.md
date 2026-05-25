# DocumentChecker

Docker Compose
```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://127.0.0.1:8000
Backend/OpenAPI through Nginx: http://127.0.0.1:8000/docs

Docker Compose (production, Nginx frontend)
```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up --build
```

Production entrypoint for the host Traefik: http://127.0.0.1:8000
Public site: https://doctest.freeddns.org
Backend/OpenAPI through Nginx: https://doctest.freeddns.org/docs

For production, Traefik should terminate HTTPS for `doctest.freeddns.org` and forward traffic to `127.0.0.1:8000`. The Docker production stack publishes only Nginx on that loopback address; Nginx serves the built frontend static files and proxies backend routes to the internal `backend:8000` service.

Keep the frontend API URL relative so Nginx proxies it:
```env
APP_BIND_ADDRESS=127.0.0.1
APP_PORT=8000
VITE_API_BASE_URL=/api
```

Models are configured in `models.yaml`, not in `.env`:
```yaml
default_model: gpt-oss:120b-cloud
models:
  - id: gpt-oss:120b-cloud
    name: GPT OSS 120B Cloud
    description: Default cloud model for document checks.
    usage_limit: 100
```

`usage_limit` is the per-user number of checks allowed for the model. Use an empty value or omit it for an unlimited model.

Predefined `.docx` templates can be placed into the `doctempletes` folder. Administrators can also upload templates from the web UI. The backend lists them through `/api/templates`, and users can select one instead of uploading a template file.

Administrators are configured in `.env`:
```env
ADMIN_LOGINS=admin@example.com,second-admin@example.com
```

Admin users can reset usage counters from the UI or through `POST /api/admin/usage/reset`.

By default the backend calls an Ollama-compatible API on the host:
`http://host.docker.internal:11434/api/chat`.

For an OpenAI-compatible API, set these values in `.env`:
```env
LLM_API_URL=
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_FORMAT=openai
AI_PROXY_KEY=sk-...
LLM_REQUESTS_PER_MINUTE=1
```

For Timeweb AI Proxy:
```env
LLM_API_URL=
LLM_API_BASE_URL=https://api.timeweb.ai/v1
LLM_API_FORMAT=openai
AI_PROXY_KEY=<YOUR_AI_PROXY_KEY>
LLM_REQUESTS_PER_MINUTE=1
```

Backend (Python/FastAPI)
```bash
pip install -r requirements.txt
python src/app/main.py
```

Frontend (Vue)
```bash
cd apps/search
npm install
npm run dev
```
