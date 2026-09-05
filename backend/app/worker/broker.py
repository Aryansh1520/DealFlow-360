"""Dramatiq broker configuration.

Imported (directly or via app.worker.tasks) by both the API process, so it can
enqueue messages, and the worker process, so it can consume them. Must be
imported before any `@dramatiq.actor` is declared, since the decorator binds
to whatever broker is globally configured at that point.
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.config.settings import settings

redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)
