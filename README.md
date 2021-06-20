# homeops

Definitions for my main Kubernetes cluster at home. Current setup:

| Hostname | IP address | Model               | Arch    | OS          |
|----------|------------|---------------------|---------|-------------|
| pinfra-1 |  10.0.0.20 | Raspberry Pi 4B 8GB | aarch64 | Raspbian 10 |
| pinfra-2 |  10.0.0.21 | Raspberry Pi 4B 8GB | aarch64 | Raspbian 10 |

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
$ USER=pi bootstrap/k3s-server pinfra-1
```

Now install `open-iscsi` for `longhorn` to consume later on:

```console
$ sudo apt update
$ sudo apt install open-iscsi
```

##### Import the sealed secrets private key

> You will have to generate your own `SealedSecrets`.

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
$ USER=pi bootstrap/k3s-agent pinfra-1 pinfra-2
```

Now install `open-iscsi` for `longhorn` to consume later on:

```console
$ sudo apt update
$ sudo apt install open-iscsi
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
NAMESPACE         NAME                                       READY   STATUS    RESTARTS   AGE     IP           NODE       NOMINATED NODE   READINESS GATES
kube-system       local-path-provisioner-7ff9579c6-q922d     1/1     Running   0          9m41s   10.42.0.3    pinfra-1   <none>           <none>
kube-system       metrics-server-7b4f8b595-2kgl2             1/1     Running   0          9m41s   10.42.0.4    pinfra-1   <none>           <none>
kube-system       coredns-66c464876b-vd4zg                   1/1     Running   0          9m41s   10.42.0.2    pinfra-1   <none>           <none>
homeops-private   helm-controller-5b96d94c7f-d6lcl           1/1     Running   0          9m14s   10.42.1.3    pinfra-2   <none>           <none>
homeops-private   notification-controller-55f94bc746-62m9q   1/1     Running   0          9m14s   10.42.1.4    pinfra-2   <none>           <none>
homeops-private   source-controller-674887ffd-dl8w2          1/1     Running   0          9m14s   10.42.0.5    pinfra-1   <none>           <none>
homeops-private   kustomize-controller-df8bb769-95pbt        1/1     Running   0          9m14s   10.42.1.2    pinfra-2   <none>           <none>
homeops           helm-controller-5b96d94c7f-jkpm5           1/1     Running   0          8m19s   10.42.1.5    pinfra-2   <none>           <none>
homeops           source-controller-674887ffd-bp2jd          1/1     Running   0          8m18s   10.42.0.7    pinfra-1   <none>           <none>
homeops           notification-controller-55f94bc746-xkvff   1/1     Running   0          8m19s   10.42.1.6    pinfra-2   <none>           <none>
homeops           kustomize-controller-df8bb769-hnt7b        1/1     Running   0          8m19s   10.42.0.6    pinfra-1   <none>           <none>
kube-system       sealed-secrets-5c6c8564d9-cxqsn            1/1     Running   0          7m32s   10.42.0.8    pinfra-1   <none>           <none>
cert-manager      cert-manager-cainjector-7b744d56fb-jhdzd   1/1     Running   0          7m9s    10.42.1.7    pinfra-2   <none>           <none>
cert-manager      cert-manager-7998c69865-g45kj              1/1     Running   0          7m8s    10.42.1.8    pinfra-2   <none>           <none>
cert-manager      cert-manager-webhook-7d6d4c78bc-84lwb      1/1     Running   0          7m9s    10.42.0.10   pinfra-1   <none>           <none>
ingress-nginx     svclb-ingress-nginx-controller-5pj6w       2/2     Running   0          6m57s   10.42.1.9    pinfra-2   <none>           <none>
ingress-nginx     svclb-ingress-nginx-controller-ln7lh       2/2     Running   0          6m57s   10.42.0.11   pinfra-1   <none>           <none>
ingress-nginx     ingress-nginx-controller-d9458694b-r852z   1/1     Running   0          6m57s   10.42.0.12   pinfra-1   <none>           <none>
pihole            svclb-pihole-dns-tcp-vrdxv                 1/1     Running   0          4m52s   10.42.1.17   pinfra-2   <none>           <none>
pihole            svclb-pihole-dns-udp-cdlhg                 2/2     Running   0          4m52s   10.42.1.18   pinfra-2   <none>           <none>
pihole            svclb-pihole-dns-tcp-h5d4h                 1/1     Running   0          4m52s   10.42.0.14   pinfra-1   <none>           <none>
pihole            svclb-pihole-dns-udp-pfsxt                 2/2     Running   0          4m52s   10.42.0.13   pinfra-1   <none>           <none>
unifi             svclb-unifi-stun-47qz4                     1/1     Running   0          4m45s   10.42.1.20   pinfra-2   <none>           <none>
unifi             svclb-unifi-controller-ntr2k               1/1     Running   0          4m45s   10.42.1.19   pinfra-2   <none>           <none>
unifi             svclb-unifi-speedtest-lr86t                1/1     Running   0          4m43s   10.42.1.21   pinfra-2   <none>           <none>
unifi             svclb-unifi-controller-r6cf8               1/1     Running   0          4m46s   10.42.0.16   pinfra-1   <none>           <none>
unifi             svclb-unifi-discovery-66mpm                1/1     Running   0          4m42s   10.42.1.22   pinfra-2   <none>           <none>
registry          registry-667874b446-9bfvv                  2/2     Running   0          5m4s    10.42.1.16   pinfra-2   <none>           <none>
unifi             svclb-unifi-stun-89b96                     1/1     Running   0          4m45s   10.42.0.17   pinfra-1   <none>           <none>
unifi             svclb-unifi-syslog-2c56v                   1/1     Running   0          4m37s   10.42.1.25   pinfra-2   <none>           <none>
unifi             svclb-unifi-discovery-mpqcv                1/1     Running   0          4m43s   10.42.0.18   pinfra-1   <none>           <none>
longhorn          longhorn-ui-cdf7cf88f-hpnpj                1/1     Running   0          4m41s   10.42.1.23   pinfra-2   <none>           <none>
unifi             svclb-unifi-speedtest-mddvb                1/1     Running   0          4m42s   10.42.0.19   pinfra-1   <none>           <none>
unifi             svclb-unifi-syslog-mtgd9                   1/1     Running   0          4m37s   10.42.0.21   pinfra-1   <none>           <none>
external-dns      external-dns-568d84c7c-czhfr               1/1     Running   0          4m36s   10.42.0.23   pinfra-1   <none>           <none>
velero            velero-856b8d7fcb-l4tpn                    1/1     Running   0          4m26s   10.42.1.27   pinfra-2   <none>           <none>
longhorn          longhorn-manager-hsbbx                     1/1     Running   0          4m37s   10.42.1.26   pinfra-2   <none>           <none>
longhorn          longhorn-driver-deployer-7b45d7556-58pj9   1/1     Running   0          4m42s   10.42.1.24   pinfra-2   <none>           <none>
longhorn          longhorn-manager-n486f                     1/1     Running   0          4m38s   10.42.0.22   pinfra-1   <none>           <none>
longhorn          instance-manager-e-307b33ba                1/1     Running   0          3m42s   10.42.1.28   pinfra-2   <none>           <none>
longhorn          instance-manager-r-494e10a0                1/1     Running   0          3m42s   10.42.1.29   pinfra-2   <none>           <none>
longhorn          engine-image-ei-611d1496-4z4lz             1/1     Running   0          3m42s   10.42.1.30   pinfra-2   <none>           <none>
longhorn          csi-attacher-76dcbccbf4-dbm2q              1/1     Running   0          2m13s   10.42.1.31   pinfra-2   <none>           <none>
longhorn          engine-image-ei-611d1496-9cskl             1/1     Running   0          3m42s   10.42.0.26   pinfra-1   <none>           <none>
longhorn          csi-provisioner-7c8fdd8db8-fsntm           1/1     Running   0          2m11s   10.42.1.32   pinfra-2   <none>           <none>
longhorn          csi-resizer-66cfcd7bd-6pwws                1/1     Running   0          2m9s    10.42.1.33   pinfra-2   <none>           <none>
longhorn          longhorn-csi-plugin-4l47n                  2/2     Running   0          2m3s    10.42.1.36   pinfra-2   <none>           <none>
longhorn          csi-snapshotter-7765db9885-q452f           1/1     Running   0          2m5s    10.42.1.34   pinfra-2   <none>           <none>
longhorn          csi-snapshotter-7765db9885-fpnq8           1/1     Running   0          2m5s    10.42.1.35   pinfra-2   <none>           <none>
longhorn          instance-manager-e-c0598308                1/1     Running   0          3m30s   10.42.0.27   pinfra-1   <none>           <none>
longhorn          instance-manager-r-c596fac3                1/1     Running   0          3m30s   10.42.0.28   pinfra-1   <none>           <none>
pihole            pihole-666649877b-lsthx                    1/1     Running   0          4m51s   10.42.0.24   pinfra-1   <none>           <none>
longhorn          csi-attacher-76dcbccbf4-zsblg              1/1     Running   0          2m13s   10.42.0.33   pinfra-1   <none>           <none>
longhorn          csi-attacher-76dcbccbf4-wm722              1/1     Running   0          2m13s   10.42.0.34   pinfra-1   <none>           <none>
longhorn          csi-provisioner-7c8fdd8db8-2n5tk           1/1     Running   0          2m12s   10.42.0.35   pinfra-1   <none>           <none>
longhorn          csi-provisioner-7c8fdd8db8-jppb6           1/1     Running   0          2m11s   10.42.0.36   pinfra-1   <none>           <none>
longhorn          longhorn-csi-plugin-tprqb                  2/2     Running   0          2m4s    10.42.0.40   pinfra-1   <none>           <none>
longhorn          csi-resizer-66cfcd7bd-rgkrp                1/1     Running   0          2m9s    10.42.0.38   pinfra-1   <none>           <none>
longhorn          csi-resizer-66cfcd7bd-pv7hx                1/1     Running   0          2m9s    10.42.0.37   pinfra-1   <none>           <none>
longhorn          csi-snapshotter-7765db9885-4jqv2           1/1     Running   0          2m5s    10.42.0.39   pinfra-1   <none>           <none>
unifi             unifi-5cddc4b847-nkx8h                     1/1     Running   0          4m41s   10.42.0.25   pinfra-1   <none>           <none>
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
