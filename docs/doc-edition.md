# Option 3: KServe - MaaS - Praxis integration

Moving the data plane from Gateway API on Istio to Praxis changes how a KServe `LLMInferenceService` receives traffic. The move exposes problems in the integration between MaaS and KServe. A status contract on the `LLMInferenceService`, with MaaS as the owner of the routing, can help in the overall migration process.

| Topic | Summary | Detail |
|---|---|---|
| Problem | MaaS and KServe integrate through the HTTPRoute | MaaS looks up the route, attaches its policies to it and derives the tenant from it. Praxis removes the per-model route. |
| Proposal | A status contract, and MaaS writes the routing | KServe publishes the backend, the port, the model names and `Ready` in the service status, with or without a route. MaaS writes the routing into the tenant's `Proxy` from it. |

## Praxis in the request path

[`gateway-controller`](https://github.com/praxis-proxy/gateway-controller) is not an ingress controller (yet?). It configures a Praxis proxy that is deployed behind the platform's existing ingress. Currently, that ingress ("any GWAPI provider, or none") "just forwards to it". A Gateway can still be the entry point and forward all traffic to Praxis. **The per-model HTTPRoute is removed**. Praxis routes on the `model` field of the request body, and ["no route is ever written"](https://github.com/praxis-proxy/gateway-controller/blob/f6a12554d9294130010ed16abea775657914bb6f/docs/design/api.md?plain=1#L311).

<picture><source media="(prefers-color-scheme: dark)" srcset="figs/request-path-dark.svg"><img src="figs/request-path.svg" alt="Request path today and with Praxis"></picture>

Today the per-model routing decision is an HTTPRoute on the Gateway. KServe writes it and Istio answers with status. With Praxis it is proxy configuration keyed on the model name, and the ingress only forwards. The EPP and the pods are the same in both columns.

### Today: who does what, and why

- KServe writes the HTTPRoute, the `InferencePool`, the EPP and the Service. The route exposes the service, and KServe derives `Ready` and the URL from the route status.
- MaaS writes the `AuthPolicy` on the Gateway and a token rate limit policy on each model's HTTPRoute. Kuadrant enforces by attaching to Gateway API objects, so a per-model limit needs a per-model route.
- Istio implements the Gateway. It adds the `ext_proc` filter for rules that target a pool, and it writes the route and pool status.
- On MaaS tenant gateways `praxis-extproc` runs as an `ext_proc` server around Kuadrant. It reads the model name from the request body, among other payload processing.

### With Praxis: who does what, and why

- The platform ingress only forwards. The proxy is not tied to any Gateway API implementation.
- MaaS creates a `Proxy` and a `Policy` per tenant. The `Policy` is a separate object so MaaS can delegate edit access without exposing the `Proxy`.
- `gateway-controller` renders the Praxis config from the `Proxy` and the `Policy`. In the Praxis design a `ModelProvider` per model also feeds the routing, and its API is still open. The rendered config has exactly one owner.
- KServe still creates the EPP, the pool, the Service and the pods. Scheduling stays with the EPP.
- Nothing writes status back to the `LLMInferenceService`. KServe readiness reads route and pool status today, so that has to change.

## Problems in today's integration

Currently, MaaS and KServe integrate through the HTTPRoute and not through a defined contract. MaaS looks up the route, attaches its policies to it and derives the tenant from it. KServe publishes the status MaaS needs only while a route exists. Praxis removes the route, so the items below have to be fixed before a service can be served through Praxis.

### Between MaaS and KServe

| Shortcoming | What it causes | Fix |
|---|---|---|
| MaaS reads KServe's HTTPRoute. There is no single contract on the `LLMInferenceService` status. | MaaS finds the route by label, checks its parent Gateway and takes the hostname from it. 42 places in the MaaS code depend on an HTTPRoute or a Gateway. Without the route a `MaaSModelRef` becomes `Pending` although the service is `Ready`. | MaaS reads the backend, the port, the model names and `Ready` from the service status, and nothing else. |
| KServe only publishes that status when a route exists. | Without a route `status.router` is empty, the address has no port and no model names, and a service with a scheduler never becomes `Ready`. | KServe publishes the same status with or without a route. |
| A MaaS policy is owned by a KServe object. | The per-model rate limit policy targets the HTTPRoute and has it as owner. Deleting the route deletes the limit. | MaaS generates per-model limits that do not attach to a route. This needs Praxis support first ([`policy#352`](https://github.com/praxis-proxy/policy/issues/352), [`policy#308`](https://github.com/praxis-proxy/policy/issues/308), or the `token_rate_limit` filter). |
| Tenant identity is bound to a Gateway. | An `AITenant` fails without a Gateway, and a model's tenant is looked up from its route's parent Gateway. The proposal allows an ingress with no Gateway API. | Keep the Gateway as the tenant's entry point, resolve the tenant from the service's `gateway.refs`, and point an `AITenant` at a `Proxy`. An ingress without Gateway API would need `spec.tenantRef`. |
| The model ID is only published on gateway addresses. | The ID clients send is a contract. MaaS takes it from `status.addresses[].models`, which KServe fills from gateway URLs only. Without a route MaaS rebuilds it from the spec, and AFAICT that misses a name set through a `baseRef` and LoRA adapter names. | KServe publishes served model names without a route. MaaS uses them as the routing key. |
| Which requests go through the EPP is only defined in the HTTPRoute. | KServe's route preset sends seven inference endpoints to the `InferencePool`, which means through the EPP, and every other path, such as `/v1/models`, directly to the workload Service. The service status names the pool, the EPP and the Service, and not which request paths belong to which. The preset is configuration and a service can carry its own route spec, so the list cannot be copied into MaaS. | KServe publishes in status which request paths go through the EPP and which go to the Service directly. MaaS writes the routing from it. |
| Canary weights only exist on a route. | `group` and `weight` are fields of `spec.router.route`, and their status needs a route. `MaaSModelRef` has no weight. A service without a route cannot take part in a canary. | Either KServe allows `group` and `weight` without a route, or MaaS holds the weights. |

## MaaSModelRef only, ModelProvider later

We propose to keep `MaaSModelRef` as the only object a user writes to publish a model. KServe publishes what it already knows about the service in its status: the backend, the port, the served model names and `Ready`, with or without a route. MaaS reads that status and writes the routing of each published model into the `Proxy` of the tenant, next to the policy slot, and `gateway-controller` renders it. No `ModelProvider` is created.

The status also has to say which request paths go through the EPP and which go to the workload Service directly. That split is only defined in the HTTPRoute today, and the routing MaaS writes needs both kinds of entries.

<picture><source media="(prefers-color-scheme: dark)" srcset="figs/relationships-option-3-dark.svg"><img src="figs/relationships-option-3.svg" alt="Custom resources in the preferred option, where MaaS writes the routing and no ModelProvider exists"></picture>

No object represents the routing of a single model. It is part of the `Proxy`, which MaaS already writes. The marks are explained in [Alternatives](alternatives.md).

### Who does what, and why

- The user writes the same `MaaSModelRef` as today. Its spec needs no new field, because the backend, the port and the model names come from the service status. Its `httpRoute*` status fields have no source without a route.
- KServe creates the pool, the EPP and the workload, and publishes the backend, the port, the served model names and `Ready` in status. It creates nothing in the tenant namespace and needs no tenant.
- MaaS reads that status and writes the routing of every published model of a tenant into the tenant's `Proxy`, next to the policy slot. The proposal allows this: when the routing slot is not delegated, "routing stays MaaS-defined". MaaS creates the `Policy` from the subscriptions and the auth policies.
- `gateway-controller` renders the `Proxy` and the `Policy`. It does not need the `ModelProvider` type, which is not implemented yet ([`#40`](https://github.com/praxis-proxy/gateway-controller/issues/40), [`#42`](https://github.com/praxis-proxy/gateway-controller/issues/42)).

### Benefits

- **One contract between MaaS and KServe**: the `LLMInferenceService` status. MaaS no longer depends on the HTTPRoute, its labels, its parent Gateway or its hostnames.
- **One writer per object.** MaaS writes every object in the tenant namespace, and KServe writes only next to the service.
- **Dependencies in one direction.** KServe needs no tenant information, creates no Praxis object and does not depend on a Praxis CRD being installed, so upstream KServe stays vendor-neutral.
- **No dependency on the `ModelProvider` API.** It is open with no milestone, and this option needs the `Proxy` and the `Policy` only.
- **Nothing changes in what users and the dashboard write.** `MaaSModelRef` needs no new spec field.
- **Several tenants per service need no extra API.** One service can be published to several tenants today, with one `MaaSModelRef` each.
- **Adopting the `ModelProvider` later needs no change for users or for KServe.** The contract with KServe and the user-facing objects stay the same.

### Costs and limits

- In the current draft a routing change rolls the proxy pods. A `Proxy` has no field for a mounted routing file, so the routing is part of the rendered configuration. The draft that renders the proxy ([`gateway-controller#82`](https://github.com/praxis-proxy/gateway-controller/pull/82)) sets a revision of that configuration as an annotation on the pod template, so the Deployment rolls on every change.
- Today it covers services without a scheduler, and no canary. The Praxis EPP client takes one static target and has no TLS. The alternatives have the same limit until that client is extended.
- All models of a tenant are in one object, so every publish and unpublish is a write to the same `Proxy`.
- The routing renderer in MaaS is discarded when the `ModelProvider` arrives. MaaS then creates one provider per `MaaSModelRef`.
- A service without a `MaaSModelRef` has no routing entry, so non-MaaS services remain on Gateway API with Kuadrant.
- When an `LLMInferenceService` is stopped or deleted, KServe removes the pool and the Service immediately, but the routing entry stays in the Praxis configuration until MaaS removes it. Until then Praxis routes requests to a backend that no longer exists, so MaaS has to remove the entry as soon as the service stops.
- Canary weights need an owner. They are either read from `group` and `weight` on the service, or defined in MaaS. We would not add a weight field to `MaaSModelRef`, because it would compete with the weight of a `ModelProvider` later.

## Changes in upstream KServe

KServe creates no new objects. It has to publish complete status for a service without a route: today such a service with a scheduler never becomes `Ready`, and its status does not include the pool. We read this from [`kserve/kserve`](https://github.com/kserve/kserve) master at [`cdbe986058`](https://github.com/kserve/kserve/commit/cdbe9860583e36f29d46a58179d86299e8faa41d). The sizes are estimates from reading the code. None of it has been implemented.

| Change | Today | Size |
|---|---|---|
| Mark a service with a scheduler and no route `Ready`, and publish its pool in `status.router.scheduler` with the v1 API group. One PR. | It stays `InferencePoolReady=False` with reason `WaitingForGateway`, and `status.router` is cleared. Both changes have to ship together because MaaS interprets "`Ready` and no pool in status" as a service without a scheduler. | Small, status only |
| Publish which request paths go through the EPP and which go to the workload Service directly. | The split exists only in the route preset. Thirteen of its sixteen rules send seven inference endpoints, such as `/v1/chat/completions`, to the `InferencePool`, and [three catch-all rules](https://github.com/kserve/kserve/blob/cdbe9860583e36f29d46a58179d86299e8faa41d/config/llmisvcconfig/config-llm-router-route.yaml#L439-L495) send every other path, such as `/v1/models`, to the workload Service. The status names the pool, the EPP and the Service, and no paths. | Medium, API change |
| Publish served model names on the address of a service with no route. | `status.addresses[].models` is filled from gateway URLs only. | Small |
| Add the port to that address, and clear `status.url` when the route is removed. | The address is the workload Service host with no port, and the Service listens on 8000. `status.url` is only written when there is a route, so AFAICT it keeps its old value once the route is removed. | Small |
| Skip the managed HTTPRoute for a Gateway that opts in, and treat the service as one with no route. | The route is always rendered when `spec.router.route` is set. A switch per Gateway has a precedent: `serving.kserve.io/model-based-routing-only` is read from the parent Gateway. | Small to medium |
| Optional: allow `group` and `weight` without a route. | They are fields of `spec.router.route`, released in v0.20.0. Validation, defaults, labels and group status all assume a route. The alternative with no KServe change is weights held by MaaS. | Medium to large |
| No change for the workload Service. | It is already in `status.workloads.service`, and a service with no scheduler and no route is already `Ready`. | None |

- Open PR [`kserve/kserve#5972`](https://github.com/kserve/kserve/pull/5972) covers a service with `gateway.refs` and no route (issue [`#5986`](https://github.com/kserve/kserve/issues/5986)). A service with no route and no refs is not covered.
- Do not make readiness wait for Praxis. MaaS waits for `Ready` before it writes the routing entry, which would create a circular dependency.
- ODH build: reconcile the scheduler before the Kuadrant auth check. Today the check returns first, so with the `AuthPolicy` CRD gone no EPP is created for a service with auth enabled.
- ODH build: give strict NetworkPolicy a way to allow the proxy's namespace. Today it takes the allowed namespaces from Gateway references only.

## Changes in MaaS

MaaS has the larger share of the work. It derives nearly all model information from the HTTPRoute today, so that dependency has to be removed first. Most rows are needed for any integration with Praxis, and only the last four follow from MaaS writing the routing. This comes from [`opendatahub-io/models-as-a-service`](https://github.com/opendatahub-io/models-as-a-service) at [`e0afdbc`](https://github.com/opendatahub-io/models-as-a-service/commit/e0afdbc2fba21070ec56e67a340f221bc448e3be).

| Change | Today | Size |
|---|---|---|
| Read the backend, the port, the model names and `Ready` from the `LLMInferenceService` status. Stop looking up the HTTPRoute. | MaaS finds the route by label and requires the tenant Gateway as its parent. No route means `Pending`, "Waiting for HTTPRoute to be created". | Medium |
| Take a model's endpoint from the tenant's ingress host, and rename the `httpRoute*` status fields. | The endpoint comes from route hostnames or Gateway listeners. `maas-api` builds the model URL from `status.httpRouteHostnames[0]`. | Medium, API change |
| Resolve the tenant from the service's `gateway.refs` when `spec.tenantRef` is empty. | It is looked up from the route's parent Gateway. The dashboard never sets `tenantRef`, so it has to stay optional. | Small |
| Write the `InferenceObjective` without checking the route. | It is only written when the model's route is on the tenant Gateway. | Small |
| Generate per-model token limits that do not attach to a route. | The rate limit policy targets the HTTPRoute and has it as owner. Praxis has to support a limit per model first. | New |
| Generate a Praxis `Policy` from `MaaSAuthPolicy`. | It becomes a Kuadrant `AuthPolicy` that targets the tenant Gateway. Kubernetes token auth waits on [`policy#213`](https://github.com/praxis-proxy/policy/issues/213). | New |
| Let an `AITenant` work without a Gateway, and create a `Proxy` and a `Policy` for it. | The tenant is set to `Failed` when its Gateway check fails, and it has no field for a `Proxy`. | New |
| Decide where `maas-api` is served. | Through the tenant Gateway, by its own HTTPRoute. Its paths include `/maas-api`, `/v1/models` and `/v1/api-keys`. | Decision |
| Write a routing entry for each `MaaSModelRef` into the tenant's `Proxy`, and remove it when the service stops or is deleted. | MaaS already does the same for an `InferenceObjective` per pool. It needs RBAC and a watch for the Praxis types. | Medium |
| Write two kinds of entries for a model with a scheduler: the inference endpoints through the EPP, and every other path to the workload Service. | MaaS has no code for this, because the HTTPRoute carries the split today. The paths have to come from the service status, and not from a list in MaaS. | New |
| Use the current model ID as the routing key. | `ResolveModelAlias` takes it from the service's status addresses, or builds `publishers/{ns}/models/{name}` from the spec. | Small |
| Decide which component owns canary weights. | `MaaSModelRef` has no weight, and two refs in one tenant with the same model ID are a conflict. | Decision, then new |

- MaaS has no Praxis control-plane code today. Nothing in the repository refers to `praxis.io`.
- Grid in [`odh-model-controller`](https://github.com/opendatahub-io/odh-model-controller) needs the first change too: it stops publishing a provider when `status.router` is empty.
