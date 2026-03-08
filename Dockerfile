# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile — Lattes XML to PDF Converter
# Base: python:3.9-slim-bookworm (Debian 12)
#
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.9-slim-bookworm AS base

# ── OS-level font installation ────────────────────────────────────────────────
# Why 'contrib' repo: ttf-mscorefonts-installer is not in Debian's 'main'
# repository (it wraps proprietary Microsoft fonts). Enabling 'contrib' is
# required and safe — it only grants access to packages wrapping non-free
# software, not non-free software itself.
# Why debconf-set-selections first: the EULA prompt is a blocking interactive
# dialog. Pre-seeding it to "true" before apt-get makes the build reproducible
# in CI/CD without TTY allocation (--no-tty / non-interactive pipelines).
# fc-cache is required so ReportLab's font lookup succeeds at runtime without
# re-registering via pdfmetrics.
# ca-certificates is required by ttf-mscorefonts-installer to fetch fonts
# from SourceForge over HTTPS during the package install phase.
RUN echo "deb http://deb.debian.org/debian bookworm contrib" >> /etc/apt/sources.list \
    && echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" \
        | debconf-set-selections \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ttf-mscorefonts-installer \
       fontconfig \
       ca-certificates \
    && fc-cache -f \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────────────────────
# Why: running a containerized interpreter as root is a violation of the
# principle of least privilege. If the process is compromised, the attacker
# gains root inside the container.
RUN groupadd --system lattes \
    && useradd  --system --gid lattes --no-create-home --shell /sbin/nologin lattes

# ── Application layer ─────────────────────────────────────────────────────────
WORKDIR /app

# Copy dependency manifest before source to exploit Docker layer cache:
# requirements.txt changes far less often than script code.
COPY requirements.txt .

# Why --no-cache-dir: avoids writing pip's wheel cache to the image layer,
# reducing the final image size without affecting runtime correctness.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy only the scripts/ directory — the root notebook and personal data
# files are excluded by .dockerignore.
COPY scripts/ ./scripts/

# Switch to the non-root user for all subsequent RUN/CMD/ENTRYPOINT calls.
USER lattes

# ── Runtime configuration ─────────────────────────────────────────────────────
# FONT_DIR is read by _register_fonts() in lattes_para_pdf.py to resolve
# Times New Roman TTF paths without hardcoding OS-specific locations.
# This follows "Config-as-Data" — the image carries the fonts; the env var
# tells the application where to find them.
ENV FONT_DIR=/usr/share/fonts/truetype/msttcorefonts

# /app/data is the single I/O boundary: the user mounts their ZIP here
# and retrieves the generated PDF from the same location.
# No personal data ever exists inside the image layers.
VOLUME ["/app/data"]

# ── Entrypoint ────────────────────────────────────────────────────────────────
# ENTRYPOINT fixes the executable; CMD provides the default argument.
# Why absolute path: using a relative path combined with -w /app/data at
# runtime would cause Python to search for the script inside /app/data/,
# where it does not exist. The absolute path resolves correctly regardless
# of the working directory set by the caller.
#   docker run ... lattes-converter CV_MYID.zip
ENTRYPOINT ["python", "/app/scripts/v1/lattes_para_pdf.py"]
CMD ["--help"]
