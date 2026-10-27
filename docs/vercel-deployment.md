# Deploy on Vercel Hobby

This project can be deployed as **one container**: the Next.js static export and FastAPI API share the same origin. Vercel detects the root `Dockerfile.vercel`, builds the image, and runs its HTTP server on `$PORT`. The existing Docker Compose file is for local use; Vercel does not run Compose.

## Before importing

- Use the public repository at `https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant` (or your fork). Select the repository root as the Vercel project root.
- Choose the free **Hobby** plan for this personal assessment/demo. Vercel restricts Hobby to personal or non-commercial use. Container functions use Fluid Compute, which `vercel.json` enables. Hobby usage is capped.
- Confirm that the Gemini key's Google AI Studio project is **Free + Active** and paid billing is disabled. Do not paste the key into Git, the frontend, or a build argument. Use Vercel's **Secret** environment-variable type.

## Import and configure

1. In Vercel, choose **Add New → Project**, import the repository, and leave the root directory at the repository root. The root `Dockerfile.vercel` is the deployment target. Deploying `frontend/` alone would leave `/api` without a backend.
2. Under **Settings → Environment Variables**, add the following to **Production** before the production deployment. Use **Secret** for the two keys:

   | Name | Value |
   | --- | --- |
   | `ANSWER_MODE` | `gemini` |
   | `GEMINI_MODEL` | `gemini-3.1-flash-lite` |
   | `GEMINI_API_KEY` | Your current working key from Google AI Studio |
   | `GEMINI_FREE_TIER_CONFIRMED` | `true` only for the verified Free + Active project |
   | `ADMIN_API_KEY` | A separate random secret of at least 32 characters |

   For Preview deployments, add a separate set only if you want public preview builds to call Gemini. Without Gemini variables, the image defaults to labeled source-reading mode.
3. Deploy or redeploy after setting variables. Vercel only applies new environment values to new deployments.

Generate an admin secret locally without printing it into the repository: `python3 -c 'import secrets; print(secrets.token_urlsafe(36))'`. Copy it directly into Vercel as a Secret. The local `backend/.env` file is excluded by `.dockerignore` and `.gitignore` and is never shipped.

## Verify the deployed URL

Open the Vercel URL and check:

```text
GET /api/health
GET /api/knowledge/status
```

Health should report `status: ok`, `knowledge_ready: true`, `answer_mode: gemini`, and `gemini_configured: true`. Ask “What treatments does ITC offer?” and confirm a cited answer from the approved clinic page. Ask an exact price question and confirm the price and source. The homepage and `/brand/placidway-logo.png` should load from the same URL.

## Storage and free-tier limits

The image contains the seven-page snapshot and the pinned ONNX MiniLM model. On each new container instance, `scripts/start_vercel.sh` links those read-only assets into `/tmp/placidway-ai-data`; the app reconstructs a writable Chroma index there. This is ephemeral. A new instance restores its own index, and a refresh does **not** permanently update future instances. Update `data/snapshot` in Git and redeploy to make new source content durable. Conversation memory, per-client rate limits, and the local daily Gemini budget are also instance-local, so they are not billing controls.

Keep Google paid billing disabled for the selected Gemini project. Vercel Hobby has its own included usage and can pause features after limits are reached. Container deployments and large Functions are currently a Vercel beta; test the real URL and cold start before treating it as a reliable assessment submission. No hosting provider can be claimed to meet a seven-day uptime requirement until measured.

References: [Vercel container deployments](https://vercel.com/changelog/bring-your-dockerfile-to-vercel-functions), [Vercel Hobby limits](https://vercel.com/docs/plans/hobby), [Vercel environment variables](https://vercel.com/docs/environment-variables), [Vercel stateless containers](https://vercel.com/kb/guide/docker-on-vercel-vs-render).
