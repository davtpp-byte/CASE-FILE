FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
# ffmpeg/ffprobe do the real video work; DejaVu is used for burned-in titles.
# gosu lets the root entrypoint fix persistent-disk ownership, then drop privileges.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg fonts-dejavu-core gosu \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 studio
COPY --chown=studio:studio . /app
COPY --chown=root:root docker-entrypoint.sh /usr/local/bin/casefile-entrypoint
RUN chmod 0755 /usr/local/bin/casefile-entrypoint \
    && mkdir -p /app/data \
    && chown -R studio:studio /app
# The entrypoint starts as root only to make /app/data (a host-mounted disk)
# writable, then execs the command below as the unprivileged studio user.
ENTRYPOINT ["/usr/local/bin/casefile-entrypoint"]
CMD ["sh", "-c", "exec python -m uvicorn app:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips='*'"]
EXPOSE 8000
