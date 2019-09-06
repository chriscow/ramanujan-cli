FROM python:3

ENV RQ_DASHBOARD_REDIS_URL=redis://redis:6379/15

# Install Python dependencies
RUN pip install rq-dashboard

ENTRYPOINT ["/bin/bash", "-c", "rq-dashboard -H redis"]