# External models

Praxis data plane, MaaS.

External models are served through objects that exist only on Gateway API and Istio today, and the Gateway's Envoy opens the connection to the provider. With Praxis as the data plane the proxy can open that connection itself, and the same question arises as for KServe models: which component writes the routing. This is a MaaS concern and is not part of the [Decision](decision.md).

| Topic | Summary | Detail |
|---|---|---|
| Today | Envoy connects to the provider | `ai-gateway-controller` chooses the provider in a Praxis `ext_proc` filter and returns the choice to Envoy through an HTTPRoute. Istio objects configure the TLS. |
| With Praxis | The proxy can connect to the provider | Praxis can connect to a provider over TLS, inject its credential and translate some API formats today. Weights work in one filter only, and failover is missing. |
| Open | Which component writes the routing | The decision covers KServe models. For external models the documents we read name three different writers. |

## External models today

An external model is a model at a provider outside the cluster, such as OpenAI or Anthropic. We read how it is modelled and routed in `ai-gateway-controller` (AGC) at [`02aa443`](https://github.com/opendatahub-io/ai-gateway-controller/commit/02aa4430a07c484a76f5dbcb338ebd726fa48863) and in MaaS at [`e0afdbc`](https://github.com/opendatahub-io/models-as-a-service/commit/e0afdbc2fba21070ec56e67a340f221bc448e3be).

### Objects

- `ExternalProvider` and `ExternalModel` are in the group `inference.opendatahub.io/v1alpha1`. Their Go types are in AGC ([`groupversion_info.go:28`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/api/inference/v1alpha1/groupversion_info.go#L28)).
- An `ExternalProvider` holds the provider type, its host name and a reference to the credential Secret ([`externalprovider_types.go:48-70`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/api/inference/v1alpha1/externalprovider_types.go#L48-L70)). An `ExternalModel` holds the model name clients use and one or more provider references, each with a target model, an API format and a weight ([`externalmodel_types.go:48-127`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/api/inference/v1alpha1/externalmodel_types.go#L48-L127)).
- A user publishes an external model with a `MaaSModelRef` whose `modelRef.kind` is `ExternalModel` ([`maasmodelref_types.go:77-90`](https://github.com/opendatahub-io/models-as-a-service/blob/e0afdbc2fba21070ec56e67a340f221bc448e3be/maas-controller/api/maas/v1alpha1/maasmodelref_types.go#L77-L90)).
- MaaS does not create the route of an external model. It takes the route name from the status of the `ExternalModel` and checks that the route exists and is accepted by the Gateway ([`providers_external.go:63-66`](https://github.com/opendatahub-io/models-as-a-service/blob/e0afdbc2fba21070ec56e67a340f221bc448e3be/maas-controller/pkg/controller/maas/providers_external.go#L63-L66)).
- AGC writes the rest. It reconciles both kinds ["into the tenant-local ExtProc overlay, credential projections, and Envoy-owned provider transport"](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/DESIGN.md?plain=1#L21-L23).

### Request path

| Step | Where | What happens |
|---|---|---|
| 1 | Gateway, before Kuadrant | A Praxis `ext_proc` server reads the model name from the request body into the header `X-Gateway-Model-Name` ([`configmap.yaml:30-45`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/config/manifests/praxis-extproc/base/config/configmap.yaml#L30-L45)). |
| 2 | Gateway, Kuadrant | Authorino and Limitador enforce the `AuthPolicy` and the `TokenRateLimitPolicy` that MaaS wrote on the HTTPRoute of the model. |
| 3 | Gateway, after Kuadrant | A second Praxis `ext_proc` server, one Deployment per tenant, runs `intelligent_route`, the translation filters when translation is enabled, and `credential_inject` ([`extproc.go:562-602`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/tenant/extproc.go#L562-L602)). The provider is chosen from the `routing-overlay` ConfigMap that AGC publishes. The credential is read from a Secret that the kubelet projects into the pod ([`extproc.go:280-282`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/tenant/extproc.go#L280-L282)). |
| 4 | Gateway, Envoy | The filter sets the header `X-AI-Routing-Candidate`, and Envoy selects the route again. A rule of the HTTPRoute `external-model-<model>` matches the header and points at an `ExternalName` Service for the provider ([`reconciler.go:2956-2966`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/controller/reconciler.go#L2956-L2966), [`:2996-2999`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/controller/reconciler.go#L2996-L2999)). |
| 5 | Gateway, Envoy | Envoy opens the TLS connection to the provider. A `ServiceEntry` makes the host reachable, and a `DestinationRule` sets the TLS mode, the SNI and an optional CA ([`reconciler.go:2813-2856`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/controller/reconciler.go#L2813-L2856)). |

- The provider is chosen at random or by weight. There is no failover: the controller ["does not add controller/ExtProc rollout coordination, health-aware selection, or retries"](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/DESIGN.md?plain=1#L61-L63), and the filter ["does not probe upstream health or retry another candidate when a selected upstream fails"](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/intelligent_route.md?plain=1#L224-L225).
- Praxis never connects to the provider in this setup. It selects the provider, and Envoy forwards the request.

### Who does what, and why

- The user writes the `ExternalProvider`, the `ExternalModel` and the credential Secret, and publishes the model with a `MaaSModelRef`.
- MaaS writes the `AuthPolicy` and the `TokenRateLimitPolicy` on the route, and takes the status of the `MaaSModelRef` from the route.
- AGC writes the routing data, the credential projections, the HTTPRoute and the Istio objects.
- Kuadrant enforces authentication and token limits in the Gateway.
- Praxis runs as two `ext_proc` servers. One reads the model name, the other chooses the provider, translates and adds the credential.
- Envoy, configured by Istio, connects to the provider.

## Dependencies on Gateway API and Istio

Every object AGC writes for the transport exists to return the choice of the provider to Envoy, or to let Envoy reach the provider. AFAICT none of them has a function when the proxy opens the connection itself. One upstream cluster per provider in the proxy configuration takes their place.

| Object | Why it exists | Written by |
|---|---|---|
| HTTPRoute `external-model-<model>` | It carries the choice of the provider back to Envoy through a header match, and it is the target of the MaaS policies. | AGC |
| `ExternalName` Service | It gives the HTTPRoute a backend for the provider. | AGC |
| `ServiceEntry` | It lets Envoy resolve and reach the host of the provider. | AGC |
| `DestinationRule` | It originates TLS to the provider, with SNI and an optional CA. | AGC |
| Two `EnvoyFilter` objects | They insert the two `ext_proc` filters around the Kuadrant filter and enable them per route ([`external-model-envoy-filter.yaml:3-66`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/config/manifests/external-model/overlays/odh/external-model-envoy-filter.yaml#L3-L66)). | AGC |
| `AuthPolicy` and `TokenRateLimitPolicy` | They attach to the HTTPRoute of the model. | MaaS |

## What AGC plans

AGC describes two modes for Praxis ([`praxis-dataplane-evolution.md:15-22`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/docs/praxis-dataplane-evolution.md?plain=1#L15-L22)). In gateway mode, which is the setup above, Praxis is an `ext_proc` side-call and Envoy opens the upstream connection. In standard mode Praxis is the tenant-facing gateway, the AI filters run in-process, and Praxis opens the connection.

- Standard mode is a draft. The document calls it ["Direction of travel from the research spike, not a committed product design"](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/docs/praxis-dataplane-evolution.md?plain=1#L133-L134), and says that authentication, quota and token accounting remain open.
- In that draft Praxis ["opens the connection to the generated KServe Service (or ExternalModel provider) without Envoy or Istio on the inference path"](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/docs/praxis-dataplane-evolution.md?plain=1#L136-L140).
- AGC is named as the component that would ["Compile Gateway / KServe / ExternalModel intent into Praxis runtime config"](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/docs/praxis-dataplane-evolution.md?plain=1#L202).
- We found no code for standard mode in AGC or in MaaS.

## What Praxis offers today

We checked what Praxis can do for an external provider when it is the proxy and not an `ext_proc` server. Most of the request path exists. Failover and egress through an HTTP proxy do not.

| Capability | State | Detail |
|---|---|---|
| Connect to a provider by host name over TLS, with SNI and a CA | Available | An upstream cluster has a CA, a client certificate, an SNI and a verify setting ([`cluster.rs:49-63`](https://github.com/praxis-proxy/praxis/blob/2212314b12a4536774f41ed4e1aec1619d403459/crates/tls/src/config/cluster.rs#L49-L63)). The CA is taken per cluster, globally or from the system trust store ([`tls.md:222-232`](https://github.com/praxis-proxy/praxis/blob/2212314b12a4536774f41ed4e1aec1619d403459/docs/operating/tls.md?plain=1#L222-L232)). |
| Inject the provider credential | Available | `credential_inject` takes the token from a file, an environment variable or an inline value, as a bearer token or an API key. A file is read again after a Secret rotation ([`credential_inject.md:20-25`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/credential_inject.md?plain=1#L20-L25)). |
| Translate API formats | Available for some pairs | AGC already uses the filters that translate Chat Completions to the Anthropic API ([`extproc.go:579-586`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/pkg/tenant/extproc.go#L579-L586)). |
| Choose between providers by weight | Available in one filter | `intelligent_route` supports `weightedRandom` with an overlay ([`intelligent_route.md:201-204`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/intelligent_route.md?plain=1#L201-L204)). `model_to_provider` maps a model to one upstream and has no weight ([`model_to_provider.md:26-31`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/model_to_provider.md?plain=1#L26-L31)). |
| Fail over to another provider | Missing | `intelligent_route` does not retry another candidate. An experimental `iterative_request_router` for provider failover exists and is off by default ([`build-features.md:166`](https://github.com/praxis-proxy/praxis/blob/2212314b12a4536774f41ed4e1aec1619d403459/docs/operating/build-features.md?plain=1#L166)). |
| Count tokens from provider responses | Available, the limit is experimental | `token_count` reads usage from streaming and non-streaming responses of five providers ([`token_count.md:10`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/token_count.md?plain=1#L10)). `token_rate_limit` is experimental and off by default ([`token_rate_limit.md:10`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/token_rate_limit.md?plain=1#L10)). |
| Reach the provider through an HTTP CONNECT proxy | Missing | We found no setting for an upstream proxy. The `forward-proxy` feature is for clients that use Praxis as their proxy, and its runtime is not merged ([`build-features.md:169`](https://github.com/praxis-proxy/praxis/blob/2212314b12a4536774f41ed4e1aec1619d403459/docs/operating/build-features.md?plain=1#L169)). |

- `intelligent_route` selects a cluster and does not define it ([`intelligent_route.md:38-40`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/intelligent_route.md?plain=1#L38-L40)). Every provider needs an upstream cluster in the proxy configuration, and a reload of the overlay cannot add one ([`:626-628`](https://github.com/praxis-proxy/ai/blob/a59c9270258a68c68f45419ef02d3f5a0a195fdd/docs/filters/intelligent_route.md?plain=1#L626-L628)).

## What the Praxis design says

The control-plane design in `gateway-controller` covers external providers with the same two objects it uses for models in the cluster. Neither is implemented ([`#40`](https://github.com/praxis-proxy/gateway-controller/issues/40), [`#42`](https://github.com/praxis-proxy/gateway-controller/issues/42)).

- A `ModelProvider` can name an external upstream URL in place of a Service, with a credential Secret and the header to present it in ([`api-v1alpha1.md:281-294`](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api-v1alpha1.md?plain=1#L281-L294)).
- The design maps `ExternalProvider` and `ExternalModel` to `ModelProvider` and `Model` as ["Near 1:1"](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api.md?plain=1#L550), and calls it a candidate for MaaS to delegate. It lists the question as open ([`api.md:621`](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api.md?plain=1#L621)).
- Weighting and failover between providers are out of scope of the first API version ([`api-v1alpha1.md:386-387`](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api-v1alpha1.md?plain=1#L386-L387)).

## Open points

The decision for KServe models has MaaS write the routing into the `Proxy` of the tenant. Nothing we read settles the same for external models. The points below are our reading of what is undefined.

- **Which component writes the routing of external models.** The AGC draft names AGC, the Praxis design suggests that MaaS delegates to `ModelProvider` and `Model`, and the decision covers KServe models only. If MaaS writes the routing of KServe models and AGC that of external models, the `Proxy` of a tenant has two writers.
- **What MaaS reads for an external model without the HTTPRoute.** The status of the `MaaSModelRef` and the targets of the policies come from that route today.
- **How the credential reaches the proxy.** Today the kubelet projects the Secret as a file into the `ext_proc` pod. The `Proxy` type offers Secret keys as environment variables only ([`proxy_types.go:41-43`](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/api/proxy/v1alpha1/proxy_types.go#L41-L43)).
- **How a private CA is trusted.** An `ExternalProvider` defines it in Istio terms, as a Secret in the Gateway namespace or a file mounted in the Gateway ([`externalprovider_types.go:65-69`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/api/inference/v1alpha1/externalprovider_types.go#L65-L69)). Praxis needs the CA as a file in its own pod.
- **Weights and failover.** Weights between providers work today. The Praxis design leaves them out of the first API version, and failover exists in neither.
- **How a new provider is added.** It needs a new upstream cluster, so it is a change of the proxy configuration and not only of the routing data.
- **Token limits.** They are as open for external models as for KServe models, and AGC lists them as open for standard mode ([`praxis-dataplane-evolution.md:203-204`](https://github.com/opendatahub-io/ai-gateway-controller/blob/02aa4430a07c484a76f5dbcb338ebd726fa48863/docs/praxis-dataplane-evolution.md?plain=1#L203-L204)).
- **Egress through an HTTP proxy.** Praxis has no upstream proxy setting, which matters for clusters that reach providers only through a proxy.

## Not verified

The findings are based on reading code and design documents. The following was not verified.

- Nothing was run on a cluster.
- The two Praxis repositories were read at [`a59c927`](https://github.com/praxis-proxy/ai/commit/a59c9270258a68c68f45419ef02d3f5a0a195fdd) and [`2212314`](https://github.com/praxis-proxy/praxis/commit/2212314b12a4536774f41ed4e1aec1619d403459). Both have moved since, so a capability listed as missing may have been added.
- That users write the `ExternalProvider` and the `ExternalModel` is inferred. We found no controller that creates them, apart from a migration of the older kind.
- How Kuadrant reads the token usage from the response of a provider.
- That no upstream proxy setting exists in Praxis is the result of a search, not a statement of the project.
