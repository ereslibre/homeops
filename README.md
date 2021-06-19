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
* `longhorn`
* `pihole`
* `sealed-secrets`
* `unifi`
* `velero`

The main definition for `flux` is at
[`flux/clusters/pinfra`](flux/clusters/pinfra).

### Bootstrap Kubernetes

You can do the initial SSH setup by touching an `ssh` file in the SD
card partition mounted in `/boot`, so when the Raspberries boot, an
SSH server is started.

The [`bootstrap`](bootstrap) folder contains scripts for bootstrapping
`k3s` and `flux`.

#### Before bootstrapping `k3s`

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

### Bootstrap Flux

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

#### Result

After some minutes, everything should be running successfully:

```
NAMESPACE        NAME                                       READY   STATUS    RESTARTS   AGE     IP           NODE       NOMINATED NODE   READINESS GATES
kube-system      metrics-server-7b4f8b595-jdtqp             1/1     Running   0          20m     10.42.0.4    pinfra-1   <none>           <none>
kube-system      local-path-provisioner-7ff9579c6-rz77d     1/1     Running   0          20m     10.42.0.3    pinfra-1   <none>           <none>
kube-system      coredns-66c464876b-zj89k                   1/1     Running   0          20m     10.42.0.2    pinfra-1   <none>           <none>
homeops-public   source-controller-6d986bbb7f-hp28k         1/1     Running   0          18m     10.42.0.5    pinfra-1   <none>           <none>
homeops-public   helm-controller-85bfd4959d-5fh22           1/1     Running   0          19m     10.42.1.2    pinfra-2   <none>           <none>
homeops-public   notification-controller-758d759586-gxtmf   1/1     Running   0          19m     10.42.1.4    pinfra-2   <none>           <none>
homeops-public   kustomize-controller-7d5959c758-xmlpj      1/1     Running   0          19m     10.42.1.3    pinfra-2   <none>           <none>
kube-system      sealed-secrets-5c6c8564d9-wns7t            1/1     Running   0          7m15s   10.42.1.5    pinfra-2   <none>           <none>
cert-manager     cert-manager-cainjector-7b744d56fb-gmzks   1/1     Running   0          6m37s   10.42.1.6    pinfra-2   <none>           <none>
cert-manager     cert-manager-7998c69865-zvmtz              1/1     Running   0          6m37s   10.42.1.7    pinfra-2   <none>           <none>
cert-manager     cert-manager-webhook-7d6d4c78bc-cf8cl      1/1     Running   0          6m37s   10.42.0.7    pinfra-1   <none>           <none>
ingress-nginx    svclb-ingress-nginx-controller-9zp6k       2/2     Running   0          6m19s   10.42.1.8    pinfra-2   <none>           <none>
ingress-nginx    svclb-ingress-nginx-controller-mrknf       2/2     Running   0          6m20s   10.42.0.9    pinfra-1   <none>           <none>
ingress-nginx    ingress-nginx-controller-d9458694b-zqbwv   1/1     Running   0          6m22s   10.42.0.8    pinfra-1   <none>           <none>
registry         registry-667874b446-pw4rj                  2/2     Running   0          6m3s    10.42.0.11   pinfra-1   <none>           <none>
external-dns     external-dns-568d84c7c-q4fx9               1/1     Running   0          5m34s   10.42.1.11   pinfra-2   <none>           <none>
longhorn         longhorn-ui-cdf7cf88f-689tx                1/1     Running   0          5m26s   10.42.1.13   pinfra-2   <none>           <none>
unifi            svclb-unifi-speedtest-nd62b                1/1     Running   0          4m51s   10.42.1.17   pinfra-2   <none>           <none>
unifi            svclb-unifi-speedtest-842gf                1/1     Running   0          4m51s   10.42.0.15   pinfra-1   <none>           <none>
unifi            svclb-unifi-discovery-488dg                1/1     Running   0          4m49s   10.42.1.18   pinfra-2   <none>           <none>
unifi            svclb-unifi-syslog-zx8bz                   1/1     Running   0          4m48s   10.42.1.19   pinfra-2   <none>           <none>
unifi            svclb-unifi-discovery-4v2md                1/1     Running   0          4m50s   10.42.0.16   pinfra-1   <none>           <none>
unifi            svclb-unifi-controller-xwwn9               1/1     Running   0          4m44s   10.42.1.21   pinfra-2   <none>           <none>
unifi            svclb-unifi-syslog-txm82                   1/1     Running   0          4m49s   10.42.0.17   pinfra-1   <none>           <none>
unifi            svclb-unifi-stun-68jg5                     1/1     Running   0          4m45s   10.42.1.20   pinfra-2   <none>           <none>
unifi            svclb-unifi-controller-4jdvt               1/1     Running   0          4m45s   10.42.0.18   pinfra-1   <none>           <none>
unifi            svclb-unifi-stun-pbczr                     1/1     Running   0          4m47s   10.42.0.19   pinfra-1   <none>           <none>
pihole           svclb-pihole-dns-tcp-cxpk4                 1/1     Running   0          4m33s   10.42.1.22   pinfra-2   <none>           <none>
pihole           svclb-pihole-dns-udp-k4mwh                 2/2     Running   0          4m32s   10.42.1.23   pinfra-2   <none>           <none>
pihole           svclb-pihole-dns-tcp-nbn8t                 1/1     Running   0          4m33s   10.42.0.21   pinfra-1   <none>           <none>
pihole           svclb-pihole-dns-udp-wvj7g                 2/2     Running   0          4m31s   10.42.0.22   pinfra-1   <none>           <none>
longhorn         longhorn-manager-msq5l                     1/1     Running   0          5m27s   10.42.1.15   pinfra-2   <none>           <none>
velero           velero-856b8d7fcb-4z2r8                    1/1     Running   0          4m27s   10.42.0.24   pinfra-1   <none>           <none>
longhorn         longhorn-driver-deployer-7b45d7556-knh57   1/1     Running   0          5m26s   10.42.1.14   pinfra-2   <none>           <none>
longhorn         instance-manager-e-ddc3f712                1/1     Running   0          3m54s   10.42.1.24   pinfra-2   <none>           <none>
longhorn         instance-manager-r-bdd6a065                1/1     Running   0          3m54s   10.42.1.25   pinfra-2   <none>           <none>
longhorn         engine-image-ei-611d1496-5txvs             1/1     Running   0          3m53s   10.42.1.26   pinfra-2   <none>           <none>
longhorn         csi-attacher-76dcbccbf4-pppfz              1/1     Running   0          2m56s   10.42.1.31   pinfra-2   <none>           <none>
longhorn         csi-attacher-76dcbccbf4-tfg2k              1/1     Running   0          2m56s   10.42.1.29   pinfra-2   <none>           <none>
longhorn         csi-attacher-76dcbccbf4-5gdzm              1/1     Running   0          2m57s   10.42.1.30   pinfra-2   <none>           <none>
longhorn         csi-provisioner-7c8fdd8db8-bhb9w           1/1     Running   0          2m54s   10.42.1.32   pinfra-2   <none>           <none>
longhorn         csi-provisioner-7c8fdd8db8-qptqt           1/1     Running   0          2m54s   10.42.1.33   pinfra-2   <none>           <none>
longhorn         csi-provisioner-7c8fdd8db8-m8f67           1/1     Running   0          2m54s   10.42.1.34   pinfra-2   <none>           <none>
longhorn         csi-resizer-66cfcd7bd-ktj4r                1/1     Running   0          2m51s   10.42.1.35   pinfra-2   <none>           <none>
longhorn         csi-resizer-66cfcd7bd-w8drh                1/1     Running   0          2m51s   10.42.1.36   pinfra-2   <none>           <none>
longhorn         csi-resizer-66cfcd7bd-vqgx7                1/1     Running   0          2m51s   10.42.1.37   pinfra-2   <none>           <none>
longhorn         longhorn-csi-plugin-b49vt                  2/2     Running   0          2m44s   10.42.1.41   pinfra-2   <none>           <none>
longhorn         csi-snapshotter-7765db9885-g2qg9           1/1     Running   0          2m45s   10.42.1.40   pinfra-2   <none>           <none>
longhorn         csi-snapshotter-7765db9885-n6lms           1/1     Running   0          2m45s   10.42.1.39   pinfra-2   <none>           <none>
longhorn         csi-snapshotter-7765db9885-g877r           1/1     Running   0          2m46s   10.42.1.38   pinfra-2   <none>           <none>
pihole           pihole-666649877b-sj879                    1/1     Running   0          4m30s   10.42.0.26   pinfra-1   <none>           <none>
unifi            unifi-6995c99b66-srkdg                     1/1     Running   1          4m46s   10.42.0.25   pinfra-1   <none>           <none>
```

### Cleanup

If you need to clean up in a quick way, you can run the uninstall
scripts provided by `k3s`.

```console
# k3s-uninstall.sh
```

On an agent node you can run:

```console
# k3s-agent-uninstall.sh
```

And then you can delete the node from Kubernetes with `k delete node
<node-name>`.
