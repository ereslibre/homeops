# homeops

Definitions for my main Kubernetes cluster at home. Current setup:

| Hostname | IP address | Model               | Arch    | OS          |
|----------|------------|---------------------|---------|-------------|
| pinfra-1 | 10.0.0.20  | Raspberry Pi 4B 8GB | armv7l  | Raspbian 10 |
| pinfra-2 | 10.0.0.21  | Raspberry Pi 4B 8GB | aarch64 | Debian 10   |

## Core stack

* `k3s` is used on all nodes for the Kubernetes service. Bootstrapping
is done through [`k3sup`](https://github.com/alexellis/k3sup). You
should already have means to SSH into the nodes before using
`k3sup`. Refer to the [project
documentation](https://github.com/alexellis/k3sup/blob/master/README.md)
to learn more.

* `flux` for defining the whole Kubernetes desired states.

### Workloads

* `cert-manager`
* `docker-registry-ui`
* `external-dns`
* `ingress-nginx`
* `longhorn`: WIP
* `pihole`
* `sealed-secrets`
* `unifi`
* `velero`: WIP

The main definition for `flux` is at
[`flux/clusters/pinfra`](flux/clusters/pinfra).

`longhorn` is targeted for `pinfra-2` exclusively, given that [armv7
is not yet
supported](https://github.com/longhorn/longhorn/issues/1997).

### Bootstrap Kubernetes

You can do the initial SSH setup by touching an `ssh` file in the SD
card partition mounted in `/boot`, so when the Raspberries boot, an
SSH server is started.

The [`bootstrap`](bootstrap) folder contains scripts for bootstrapping
`k3s` and `flux`.

#### Before boostrapping `k3s`

Update `/boot/cmdline.txt` and add the following towards the end:

```
cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory
```

This ensures the `k3s` agent -- essentially the Kubernetes `kubelet`
-- will work as expected.

#### `pinfra-1`

##### Bootstrap the `k3s` server

From within the private network, I execute:

```console
$ bootstrap/k3s-server pinfra-1
```

##### Import the sealed secrets private key

> Note: if you are an external user, the `SealedSecrets` included in
> this repository won't be usable and you'll have to generate a
> key pair and generate your own `SealedSecrets`.

Before we deploy anything, we have to restore the private key (a
regular Kubernetes `Secret`)used to decipher the `SealedSecrets` in
this repository. The private key is not in this repositoy, as it
contains `SealedSecrets` with sensitive contents.

The private key is stored in a safe place I can restore it from, so I
can reuse the `SealedSecrets` you see on this repository.

```console
$ KUBECONFIG=kubeconfig k apply -f /secret/place/pinfra-master-key.yaml
```

#### `pinfra-2`

```console
$ bootstrap/k3s-agent pinfra-1 pinfra-2
```

##### Taint node

`pinfra-2` is only meant to run storage workloads, so we want to avoid
general workloads to land in this node. And so, we taint the node.

```console
$ KUBECONFIG=kubeconfig k taint nodes pinfra-2 dedicated=storage:NoSchedule
```

### Bootstrap Flux (and all workloads as a result)

Create a GitHub Personal Access Token (PAT) in your [account
settings](https://github.com/settings/tokens). This is so `flux` can
create a GitHub Deploy Key and push changes back to the repository.

```console
$ KUBECONFIG=kubeconfig GITHUB_TOKEN=$(cat /secret/place/gh-token) bootstrap/flux
```

This will deploy `flux` and add this repository to the `flux`
definitions.

Now it's time to wait until all workloads are correctly running in
your cluster.

### Cleanup

For cleaning up in a quick way and retry the bootstrap if needed, you
can SSH into the node to be cleaned up and execute:

```console
# k3s-uninstall.sh
```

On an agent node you can run:

```console
# k3s-agent-uninstall.sh
```

And then you can delete the node from Kubernetes with `k delete node
<node-name>`.
