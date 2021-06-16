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
* `velero`: WIP

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
NAMESPACE       NAME                                       READY   STATUS    RESTARTS   AGE     IP           NODE       NOMINATED NODE   READINESS GATES
kube-system     metrics-server-7b4f8b595-7w6dq             1/1     Running   0          15m     10.42.0.3    pinfra-1   <none>           <none>
kube-system     local-path-provisioner-7ff9579c6-qbp2s     1/1     Running   0          15m     10.42.0.4    pinfra-1   <none>           <none>
kube-system     coredns-66c464876b-tp6lr                   1/1     Running   0          15m     10.42.0.2    pinfra-1   <none>           <none>
flux-system     source-controller-6d986bbb7f-pkblx         1/1     Running   0          14m     10.42.0.5    pinfra-1   <none>           <none>
flux-system     kustomize-controller-7d5959c758-w7x59      1/1     Running   0          14m     10.42.1.4    pinfra-2   <none>           <none>
flux-system     notification-controller-758d759586-hj2rj   1/1     Running   0          14m     10.42.1.3    pinfra-2   <none>           <none>
flux-system     helm-controller-85bfd4959d-7pq6l           1/1     Running   0          14m     10.42.1.2    pinfra-2   <none>           <none>
kube-system     sealed-secrets-5c6c8564d9-xlcqq            1/1     Running   0          12m     10.42.0.6    pinfra-1   <none>           <none>
cert-manager    cert-manager-cainjector-7b744d56fb-8m4qf   1/1     Running   0          12m     10.42.0.7    pinfra-1   <none>           <none>
ingress-nginx   svclb-ingress-nginx-controller-2jn75       2/2     Running   0          11m     10.42.0.8    pinfra-1   <none>           <none>
cert-manager    cert-manager-7998c69865-qnvgl              1/1     Running   0          12m     10.42.1.7    pinfra-2   <none>           <none>
cert-manager    cert-manager-webhook-7d6d4c78bc-2mlwf      1/1     Running   0          12m     10.42.1.6    pinfra-2   <none>           <none>
ingress-nginx   svclb-ingress-nginx-controller-bfk8k       2/2     Running   0          11m     10.42.1.9    pinfra-2   <none>           <none>
registry        registry-667874b446-875gm                  2/2     Running   0          11m     10.42.0.10   pinfra-1   <none>           <none>
ingress-nginx   ingress-nginx-controller-d9458694b-85mlr   1/1     Running   0          11m     10.42.1.8    pinfra-2   <none>           <none>
external-dns    external-dns-568d84c7c-cbdcw               1/1     Running   0          10m     10.42.1.12   pinfra-2   <none>           <none>
longhorn        longhorn-ui-cdf7cf88f-j7vmt                1/1     Running   0          10m     10.42.1.13   pinfra-2   <none>           <none>
pihole          svclb-pihole-dns-tcp-75gzw                 1/1     Running   0          9m31s   10.42.0.29   pinfra-1   <none>           <none>
pihole          svclb-pihole-dns-udp-sq4bj                 2/2     Running   0          9m29s   10.42.0.31   pinfra-1   <none>           <none>
pihole          svclb-pihole-dns-udp-7b7dk                 2/2     Running   0          9m29s   10.42.1.32   pinfra-2   <none>           <none>
pihole          svclb-pihole-dns-tcp-zjglf                 1/1     Running   0          9m31s   10.42.1.31   pinfra-2   <none>           <none>
longhorn        longhorn-manager-7cx5k                     1/1     Running   0          10m     10.42.1.15   pinfra-2   <none>           <none>
pihole          pihole-666649877b-dlcqx                    1/1     Running   0          9m29s   10.42.0.33   pinfra-1   <none>           <none>
longhorn        longhorn-driver-deployer-7b45d7556-xw5r5   1/1     Running   0          10m     10.42.1.14   pinfra-2   <none>           <none>
longhorn        instance-manager-r-c773f7fc                1/1     Running   0          8m46s   10.42.1.35   pinfra-2   <none>           <none>
longhorn        instance-manager-e-cf7df789                1/1     Running   0          8m47s   10.42.1.34   pinfra-2   <none>           <none>
longhorn        engine-image-ei-611d1496-cshzl             1/1     Running   0          8m46s   10.42.1.36   pinfra-2   <none>           <none>
longhorn        csi-attacher-5f56cf6c9f-8kmzw              1/1     Running   0          5m43s   10.42.1.39   pinfra-2   <none>           <none>
longhorn        csi-resizer-9b75bd77c-xlqms                1/1     Running   0          5m41s   10.42.1.46   pinfra-2   <none>           <none>
longhorn        csi-snapshotter-757bd96656-96sz6           1/1     Running   0          5m40s   10.42.1.48   pinfra-2   <none>           <none>
longhorn        longhorn-csi-plugin-hgw68                  2/2     Running   0          5m39s   10.42.1.51   pinfra-2   <none>           <none>
longhorn        csi-provisioner-8494659d9-8qlpz            1/1     Running   0          5m42s   10.42.1.44   pinfra-2   <none>           <none>
longhorn        csi-attacher-5f56cf6c9f-wzv5v              1/1     Running   0          5m43s   10.42.1.41   pinfra-2   <none>           <none>
longhorn        csi-provisioner-8494659d9-n9m9d            1/1     Running   0          5m42s   10.42.1.42   pinfra-2   <none>           <none>
longhorn        csi-provisioner-8494659d9-m78qc            1/1     Running   0          5m42s   10.42.1.43   pinfra-2   <none>           <none>
longhorn        csi-attacher-5f56cf6c9f-zsfkr              1/1     Running   0          5m43s   10.42.1.40   pinfra-2   <none>           <none>
longhorn        csi-resizer-9b75bd77c-7sd6g                1/1     Running   0          5m41s   10.42.1.45   pinfra-2   <none>           <none>
longhorn        csi-resizer-9b75bd77c-bnfdh                1/1     Running   0          5m41s   10.42.1.47   pinfra-2   <none>           <none>
longhorn        csi-snapshotter-757bd96656-pgwkl           1/1     Running   0          5m40s   10.42.1.50   pinfra-2   <none>           <none>
longhorn        csi-snapshotter-757bd96656-7bgk7           1/1     Running   0          5m40s   10.42.1.49   pinfra-2   <none>           <none>
unifi           svclb-unifi-speedtest-qgqv6                1/1     Running   0          3m45s   10.42.1.57   pinfra-2   <none>           <none>
unifi           svclb-unifi-controller-vbwms               1/1     Running   0          3m44s   10.42.1.58   pinfra-2   <none>           <none>
unifi           svclb-unifi-syslog-lfrbr                   1/1     Running   0          3m42s   10.42.1.59   pinfra-2   <none>           <none>
unifi           svclb-unifi-stun-2n55z                     1/1     Running   0          3m41s   10.42.1.60   pinfra-2   <none>           <none>
unifi           svclb-unifi-discovery-29cnb                1/1     Running   0          3m43s   10.42.0.40   pinfra-1   <none>           <none>
unifi           svclb-unifi-syslog-bhwnx                   1/1     Running   0          3m42s   10.42.0.41   pinfra-1   <none>           <none>
unifi           svclb-unifi-stun-7cmth                     1/1     Running   0          3m42s   10.42.0.42   pinfra-1   <none>           <none>
unifi           svclb-unifi-discovery-7p9gm                1/1     Running   0          3m44s   10.42.1.61   pinfra-2   <none>           <none>
unifi           svclb-unifi-speedtest-rtcbm                1/1     Running   0          3m45s   10.42.0.44   pinfra-1   <none>           <none>
unifi           svclb-unifi-controller-lxzfr               1/1     Running   0          3m45s   10.42.0.45   pinfra-1   <none>           <none>
unifi           unifi-6995c99b66-p26nb                     1/1     Running   0          3m43s   10.42.0.43   pinfra-1   <none>           <none>
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
