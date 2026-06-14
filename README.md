# homeops

Definitions for my main Kubernetes cluster at home.

## Layout

- `flux/clusters/pinfra` — the cluster entrypoint. The `homeops` Kustomization
  reconciles this path and points at the other Kustomizations (`apps`, `infra`,
  `sealed-secrets`, `helm-repos`, `misc`).
- `flux/apps/pinfra` — applications, managed by the `apps` Kustomization
  (namespace `homeops`). Its source is the `homeops` GitRepository, which tracks
  the `main` branch of this repo on GitHub.
- `flux/apps/base` — base manifests overlaid by the per-cluster app definitions.

## Forcing a reconcile

Flux polls the `homeops` GitRepository every minute and re-applies every 10
minutes. To pick up a change immediately after pushing it to `main`, reconcile
the relevant Kustomization with its source:

```bash
# Apps (teslamate and everything else under flux/apps/pinfra)
flux reconcile kustomization apps -n homeops --with-source
```

`--with-source` first re-pulls the `homeops` GitRepository from GitHub, then
re-applies the `apps` Kustomization. The change must already be pushed to `main`
— Flux pulls from GitHub, not from your local working tree.

Make sure the right cluster is selected first (e.g. `export KUBECONFIG=...`).

## Development Environment

This project needs the `flux` and `kubectl` CLIs. If they are not installed, run
them on demand via [nixomatic](https://nixomatic.com):

### Using Nix

```bash
nix \
    --extra-experimental-features 'nix-command flakes' \
    develop 'https://nixomatic.com/?p=fluxcd,kubectl' \
      --accept-flake-config
```

### Using Docker

```bash
docker run -v nix-store:/nix -v "$PWD:/workspace" -w /workspace --rm -it nixos/nix nix \
    --extra-experimental-features 'nix-command flakes' \
    develop 'https://nixomatic.com/?p=fluxcd,kubectl' \
      --accept-flake-config
```
