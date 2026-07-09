# CheckMyCoach Dockerfile
# 
# NOTE: Knowledge Compiler is a separate repo (acsms12-manifest).
# For now, the recommended way to run is:
#   pip install pyyaml requests python-dotenv mcp
#   python cli.py "Your question"
#
# This Dockerfile works when acsms12-manifest is available at ../acsms12-manifest.
# Phase 0 confirmed pip install -e fails due to setuptools bug;
# sys.path fallback is used instead.

FROM python:3.12-slim

WORKDIR /app

# Install runtime deps (KC deps: pyyaml)
RUN pip install --no-cache-dir \
    pyyaml>=6.0 \
    requests>=2.28 \
    python-dotenv>=1.0 \
    mcp>=1.0

# Copy CheckMyCoach
COPY . .

# KC will be loaded via sys.path at runtime
# (expects C:\Users\gbx12\projects\acsms12-manifest on host)

ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
