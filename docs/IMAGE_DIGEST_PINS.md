# Image digest pins for production builds (audit 2026-10-02 §13).
#
# Dockerfile.prod pins base images by digest (refreshed 2026-10-02):
#
#   rust:1-bookworm@sha256:59037199c44290f2befcdd58dcc540164763fc296950255aaefeef096a1866b0
#   python:3.13-slim@sha256:bb2988715db2cf7ace7b53f38f3cffbef7c7046a656bee66245eb0ed386e2e81
#
# Application image: prefer digest after bake, not `:latest` / `:local` alone.
#
#   docker build -f Dockerfile.prod -t abs-blockchain-prod:local .
#   $digest = (docker image inspect abs-blockchain-prod:local --format '{{index .RepoDigests 0}}')
#   # or record Image ID:
#   docker image inspect abs-blockchain-prod:local --format '{{.Id}}'
#
# Compose override example:
#
#   ABS_PROD_IMAGE=abs-blockchain-prod@sha256:<digest>
#
# Refresh digests when intentionally upgrading base images; commit Dockerfile.prod
# + this note together. Do not claim fleet reproducibility from floating tags.
