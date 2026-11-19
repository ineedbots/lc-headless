# Build for Synology DSM

The Debian 12 builder targets x86-64 Synology NAS systems with glibc 2.36.
Run it on the NAS with Container Manager or on an x86-64 machine with Docker
Compose and Linux containers enabled.

## Build

Run these commands from the repository root. On DSM, use `sudo` if your SSH
account requires it for Docker.

```sh
docker compose -f tools/docker/dsm/compose.dsm.yml build dsm-build
docker compose -f tools/docker/dsm/compose.dsm.yml run --rm dsm-build
```

The service uses two parallel build jobs by default. Set `DSM_BUILD_JOBS` in
your shell to change that limit. The named `dsm-build` volume keeps the build
tree and vcpkg cache for subsequent runs.

## Run on DSM

Copy `build/dsm/Rs2004Headless-dsm` and the entire `build/dsm/dsm-runtime/`
directory into your app folder on the NAS. Keep the client configuration,
accounts, cache, and scripts there as described in the
[running guide](../../../docs/Running.md#first-login).

Run these commands from the app folder on the NAS. The executable loads the
bundled C++ runtime and DSM's glibc.

```sh
chmod +x Rs2004Headless-dsm
LD_LIBRARY_PATH="$PWD/dsm-runtime" ./Rs2004Headless-dsm
```
