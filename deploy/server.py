"""One process for a small free host (Render, 512 MB): `uvicorn deploy.server:app`.

Locally the agent API, the evaluation API and the three mock providers are separate services
(docker-compose.yml, Quickstart). This entrypoint serves them all from one process so the demo
fits one free instance; nothing in app/ or evals/ changes for it.

- The mocks are mounted under /mock/payments, /mock/shipping and /mock/ticketing. The agent
  still reaches them over HTTP at MOCK_*_URL with their API keys, like any other provider.
- The evaluation API and UI (/eval, /ui) are mounted only when EVAL_DATABASE_URL is set, and
  read that database: experiments run in their own database (see scripts/dev.py).
- Before the port opens, the policies are ingested and the embedding model and checkpointer
  are loaded once. On a small shared CPU loading the model takes minutes; done lazily, the
  first run held a database transaction open that long and Neon closed it.
"""

import os
import time
from collections.abc import Iterator

from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import get_db, get_engine
from app.main import create_app
from app.policies.documents import load_policies
from app.policies.embeddings import get_embedder
from app.workflows.checkpoints import get_checkpointer
from mock_services.payments.main import app as payments
from mock_services.shipping.main import app as shipping
from mock_services.ticketing.main import app as ticketing
from scripts.ingest_policies import ingest


def warm_up() -> None:
    started = time.monotonic()
    embedder = get_embedder()
    print(f"warm-up: embedding model loaded in {time.monotonic() - started:.0f}s", flush=True)
    with get_engine().begin() as connection:
        result = ingest(connection, embedder, load_policies())
    print(
        f"warm-up: policies {len(result.inserted)} inserted, {len(result.replaced)} replaced, "
        f"{len(result.unchanged)} unchanged",
        flush=True,
    )
    get_checkpointer()
    print(f"warm-up: done in {time.monotonic() - started:.0f}s", flush=True)


warm_up()

app = create_app()


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    """The bare URL is what people open first: send them to the demo screen."""
    return RedirectResponse("/demo")


app.mount("/mock/payments", payments)
app.mount("/mock/shipping", shipping)
app.mount("/mock/ticketing", ticketing)

eval_database_url = os.environ.get("EVAL_DATABASE_URL")
if eval_database_url:
    from evals.api import create_app as create_eval_app

    eval_engine = create_engine(
        eval_database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5}
    )

    def get_eval_db() -> Iterator[Session]:
        with Session(eval_engine) as session:
            yield session

    eval_app = create_eval_app()
    eval_app.dependency_overrides[get_db] = get_eval_db
    # Mounted last: it only sees paths the agent API does not serve (/eval/..., /ui/...).
    app.mount("/", eval_app)
