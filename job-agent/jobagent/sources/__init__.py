"""채용 소스 레지스트리. 각 모듈은 fetch(queries, **opts) -> list[Job] 를 제공."""
from . import jobkorea, linkedin, remember, saramin, wanted

REGISTRY = {
    "wanted": wanted.fetch,
    "linkedin": linkedin.fetch,
    "saramin": saramin.fetch,
    "jobkorea": jobkorea.fetch,
    "remember": remember.fetch,
}
