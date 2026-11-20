"""The figures, one function each.

A function returns a `Fig` and registers under a name with `@figure`. A page source
places the figure with `<!-- figure: NAME -->`, and the standalone files are
`docs/figs/NAME.svg` and `docs/figs/NAME-dark.svg`.

Encoding of the relationship maps: a tile's colour and header label name who writes the
object, a tile indented under another is owned by it (ownerReference), a solid edge is a
reference held in a field, a dashed edge is a controller acting without a reference, and
red marks a relationship listed as a shortcoming.
"""
from typing import Callable, NamedTuple

from errors import require
from figkit import Fig, Lane, RelFig, left, right


class Figure(NamedTuple):
    build: Callable[[], Fig]
    alt: str


FIGURES = {}


def figure(name, alt):
    """Register the decorated function as the figure `name`. `alt` is the short
    alternative text of the image in Markdown."""
    def register(build):
        require(name not in FIGURES, f"figure {name} is registered twice")
        FIGURES[name] = Figure(build, alt)
        return build
    return register


# --- ingress-paths ---------------------------------------------------------------

@figure("request-path", "Request path today and with Praxis")
def request_path():
    f = Fig(
        "f1", 1040, 502,
        "Request path today and with Praxis, as stacks of layers. Today the request goes through an Istio "
        "Gateway that stacks payload processing, Kuadrant, a per-model HTTPRoute and an ext_proc filter. In the "
        "target setup the platform ingress only forwards to a Praxis proxy that stacks a policy slot and a routing "
        "slot. The per-model routing decision moves from the HTTPRoute to the routing slot.",
    )
    W, TW = 476, 452
    L, R = 16, 548

    # left column: today
    f.title(L, 20, "TODAY: GATEWAY API ON ISTIO", "gw")
    cx = L + W / 2
    f.plain(cx - 60, 36, 120, 36, "Client")
    f.edge([(cx, 72), (cx, 104)])
    f.group(L, 104, W, 278, "Gateway (Envoy, Istio)", "gw")
    x = L + 12
    f.tile(x, 128, TW, 54, "Payload processing", "MaaS gateways only",
           ["praxis-extproc as an ext_proc server, before and after Kuadrant"], icon="ext")
    f.tile(x, 190, TW, 54, "Kuadrant", "MaaS writes the policies",
           ["Authorino for auth, Limitador for token limits per HTTPRoute"], icon="shield")
    f.tile(x, 252, TW, 54, "HTTPRoute, one per model", "KServe writes it",
           ["path, header and weight, to a pool or a Service"], accent="warn", icon="route")
    f.tile(x, 314, TW, 54, "ext_proc filter", "per rule that targets a pool",
           ["asks the EPP which pod to use"], icon="ext")

    # right column: proposal
    f.title(R, 20, "WITH PRAXIS: PROXY BEHIND THE PLATFORM INGRESS", "px")
    cx = R + W / 2
    f.plain(cx - 60, 36, 120, 36, "Client")
    f.edge([(cx, 72), (cx, 104)])
    x = R + 12
    f.tile(x, 104, TW, 54, "Platform ingress", "forwards only",
           ["any Gateway API provider, or a LoadBalancer Service"], icon="hex")
    f.edge([(cx, 158), (cx, 190)])
    f.group(R, 190, W, 192, "Praxis proxy, one per tenant", "px")
    f.tile(x, 214, TW, 70, "Policy slot (PPE)", "MaaS creates the Policy",
           ["auth and token limits", "rendered by gateway-controller into the policy filter"], icon="shield")
    f.tile(x, 292, TW, 70, "Routing slot", "MaaS writes it",
           ["pick by published model name", "then the EPP call, over ext_proc"], accent="warn", icon="route")

    # the piece that moves
    f.edge([(L + 12 + TW, 279), (520, 279), (520, 327), (R + 12, 327)], accent="warn", dash=True)
    f.pill(520, 303, "moves", "warn")

    # backends, same in both columns
    for x0, req in ((L, "to the picked pod, or the Service"), (R, "to the picked pod")):
        f.edge([(x0 + 85, 382), (x0 + 85, 436)], both=True)
        f.pill(x0 + 85, 409, "ext_proc")
        f.edge([(x0 + 338, 382), (x0 + 338, 436)])
        f.pill(x0 + 338, 409, req)
        f.tile(x0, 436, 170, 54, "EPP", "KServe", ["picks the pod"], icon="ext")
        f.tile(x0 + 200, 436, 276, 54, "vLLM pods", "created by KServe",
               ["behind an InferencePool or a Service"], icon="pool")
    f.legend([
        ("tile", "warn", "carries the per-model routing decision"),
        ("line", "", "request"),
        ("dash", "warn", "where that decision moves"),
        ("group", "", "one proxy and the layers inside it"),
        (None, "", "label on the right of a tile: who writes it, or where it applies"),
    ])
    return f


# --- external-models -------------------------------------------------------------

@figure("external-request-path", "Request path of an external model today and with Praxis as the proxy")
def external_request_path():
    f = Fig(
        "f4", 1040, 588,
        "Request path of an external model, as stacks of layers. Today the request goes through the Istio "
        "Gateway, where two ext_proc filters call Praxis servers around Kuadrant, an HTTPRoute matches the chosen "
        "provider, and Envoy connects to the provider with a ServiceEntry and a DestinationRule. With Praxis as "
        "the proxy, the tenant Gateway forwards to the proxy, which chooses the provider, adds the credential and "
        "connects to the provider through an upstream cluster.",
    )
    W, TW = 476, 452
    L, R = 16, 548

    # left column: today
    f.title(L, 20, "TODAY: ENVOY CONNECTS TO THE PROVIDER", "gw")
    cx = L + W / 2
    f.plain(cx - 60, 36, 120, 36, "Client")
    f.edge([(cx, 72), (cx, 104)])
    f.group(L, 104, W, 340, "Gateway (Envoy, Istio)", "gw")
    x = L + 12
    f.tile(x, 128, TW, 54, "ext_proc filter, before Kuadrant", "calls Praxis",
           ["reads the model name from the request body"], icon="ext")
    f.tile(x, 190, TW, 54, "Kuadrant", "MaaS writes the policies",
           ["auth and token limits on the HTTPRoute of the model"], icon="shield")
    f.tile(x, 252, TW, 54, "ext_proc filter, after Kuadrant", "calls Praxis",
           ["chooses the provider and adds the credential"], icon="ext")
    f.tile(x, 314, TW, 54, "HTTPRoute, one per model", "AGC writes it",
           ["matches the chosen provider, to an ExternalName Service"], icon="route")
    f.tile(x, 376, TW, 54, "ServiceEntry, DestinationRule", "AGC writes them",
           ["host, TLS, SNI and CA of the provider"], accent="warn", icon="hex")

    # right column: Praxis as the proxy, following the AGC draft
    f.title(R, 20, "WITH PRAXIS (DRAFT): THE PROXY CONNECTS TO THE PROVIDER", "px")
    cx = R + W / 2
    f.plain(cx - 60, 36, 120, 36, "Client")
    f.edge([(cx, 72), (cx, 104)])
    x = R + 12
    f.tile(x, 104, TW, 54, "Tenant Gateway", "forwards only",
           ["one route to the proxy of the tenant"], icon="hex")
    f.edge([(cx, 158), (cx, 190)])
    f.group(R, 190, W, 278, "Praxis proxy, one per tenant", "px")
    f.tile(x, 214, TW, 54, "Policy slot", "open for external models",
           ["auth and token limits"], icon="shield")
    f.tile(x, 276, TW, 54, "intelligent_route", "writer is open",
           ["chooses the provider by model name and weight"], icon="route")
    f.tile(x, 338, TW, 54, "credential_inject, translation", "in-process",
           ["adds the credential, translates the API format"], icon="ext")
    f.tile(x, 400, TW, 54, "Upstream cluster, one per provider", "writer is open",
           ["host, TLS, SNI and CA of the provider"], accent="warn", icon="hex")

    # the piece that moves
    f.edge([(L + 12 + TW, 403), (520, 403), (520, 427), (R + 12, 427)], accent="warn", dash=True)
    f.pill(520, 415, "moves", "warn")

    # what is called from the Gateway or the proxy
    f.edge([(L + 85, 444), (L + 85, 522)], both=True)
    f.pill(L + 85, 483, "ext_proc")
    f.tile(L, 522, 200, 54, "Praxis ext_proc", "AGC", ["two servers per tenant"], icon="ext")
    for x0, top in ((L, 444), (R, 468)):
        f.edge([(x0 + 348, top), (x0 + 348, 522)])
        f.pill(x0 + 348, (top + 522) / 2 - 4, "TLS to the provider")
        f.tile(x0 + 220, 522, 256, 54, "Provider", "outside the cluster",
               ["such as OpenAI or Anthropic"], icon="pool")
    f.legend([
        ("tile", "warn", "connects to the provider"),
        ("line", "", "request"),
        ("dash", "warn", "where that moves"),
        ("group", "", "one proxy and the layers inside it"),
        (None, "", "label on the right of a tile: who writes it, or its state"),
    ])
    return f


# --- migration -------------------------------------------------------------------

@figure("migration-stages", "Client request path in the four migration stages")
def migration_stages():
    # Four columns with the same slots, so that a layer that is added or removed shows as
    # a filled or an empty slot at the same height.
    f = Fig(
        "f3", 1040, 612,
        "Client request path in the four migration stages. In stage 1 and stage 2 the request goes through the "
        "tenant Gateway, Kuadrant and the per-model HTTPRoute to the pods. In stage 2 a Praxis proxy and a "
        "forwarding route exist, and only test traffic reaches the proxy. In stage 3 the per-model routes are "
        "removed and the forwarding route sends model requests to the Praxis proxy. In stage 4 the Kuadrant "
        "policies are removed from the Gateway.",
    )
    COL, GW, TW = 256, 206, 186
    stages = (
        ("1. PREPARE", "gw"),
        ("2. PRAXIS NEXT TO THE ROUTES", "gw"),
        ("3. CUT-OVER OF A TENANT", "px"),
        ("4. CLEAN-UP", "px"),
    )
    for i, (title, accent) in enumerate(stages):
        x0 = 14 + i * COL
        cx, x, bypass = x0 + GW / 2, x0 + 10, x0 + 224
        praxis, cut_over = i >= 1, i >= 2

        f.title(x0, 20, title, accent)
        f.plain(cx - 50, 34, 100, 32, "Client")
        f.edge([(cx, 66), (cx, 96)])

        f.group(x0, 96, GW, 214, "Tenant Gateway (Istio)", "gw")
        if i < 3:
            f.tile(x, 120, TW, 54, "Kuadrant", None,
                   ["gateway-level policies" if cut_over else "auth and token limits"], icon="shield")
        else:
            f.text(cx, 151, "Kuadrant policies removed", anchor="middle")
        if cut_over:
            f.text(cx, 213, "per-model routes removed", anchor="middle")
        else:
            f.tile(x, 182, TW, 54, "HTTPRoute per model", None, ["serves every client request"],
                   accent="warn", icon="route")
        if praxis:
            f.tile(x, 244, TW, 54, "Forwarding route", None,
                   ["all model requests" if cut_over else "outranked by model routes"], icon="route")

        if praxis:
            f.group(x0, 346, GW, 152, "Praxis proxy", "px")
            f.tile(x, 370, TW, 54, "Policy slot", None, ["auth and token limits"], icon="shield")
            f.tile(x, 432, TW, 54, "Routing slot", None, ["backend by model name"],
                   accent="warn" if cut_over else "", icon="route")
        else:
            f.text(cx, 425, "No Praxis objects yet", anchor="middle")

        if cut_over:
            f.edge([(cx, 310), (cx, 346)])
            f.edge([(cx, 498), (cx, 546)])
        else:
            # The request leaves the Gateway at the per-model route and passes the proxy by.
            f.edge([(x0 + GW, 209), (bypass, 209), (bypass, 546)])
            f.pill(bypass, 328, "request")
            if praxis:
                f.edge([(cx, 498), (cx, 546)], dash=True)
                f.pill(cx, 522, "test traffic")

        f.tile(x0, 546, 240, 54, "EPP and vLLM pods", None, ["the same pods in every stage"], icon="pool")

    f.legend([
        ("line", "", "client request"),
        ("dash", "", "test traffic, addressed to the proxy directly"),
        ("tile", "warn", "carries the per-model routing decision"),
        ("group", "", "one proxy and the layers inside it"),
    ])
    return f


# --- cr-relationships ------------------------------------------------------------

@figure("relationships-today", "Custom resources today, on Gateway API with Kuadrant")
def relationships_today():
    f = RelFig("r1", 1040, 550,
               "Custom resources today. The LLMInferenceService owns the HTTPRoute, the InferencePool and the EPP. "
               "The HTTPRoute references the tenant Gateway and owns the per-model TokenRateLimitPolicy that MaaS "
               "writes. MaaSModelRef references the service and the AITenant and takes its status from the "
               "HTTPRoute. The AITenant references the Gateway, which owns the AuthPolicy.")
    t = Lane(f, "T", "Tenant namespaces")
    ten = t.add("AITenant", "platform admin", ["spec.gateway: the tenant Gateway"])
    sub = t.add("MaaSSubscription", "admin", ["token limits per model"])
    auth = t.add("MaaSAuthPolicy", "admin", ["who may call which model"])
    t.add("maas-api, HTTPRoute", "MaaS", ["route attached to the Gateway"], "maas")
    t.close()

    m = Lane(f, "M", "Model namespace")
    ref = m.add("MaaSModelRef", "user", ["modelRef: LLMInferenceService", "status derived from the HTTPRoute"])
    svc = m.add("LLMInferenceService", "user", ["gateway.refs: the tenant Gateway"])
    route = m.add("HTTPRoute", "KServe", ["backendRefs: pool, Service"], "ks", 1)
    trlp = m.add("TokenRateLimitPolicy", "MaaS", ["targetRef: the HTTPRoute"], "maas", 2)
    pool = m.add("InferencePool", "KServe", ["endpointPickerRef: EPP Service"], "ks", 1)
    epp = m.add("EPP, workload", "KServe", ["Deployments and Services"], "ks", 1)
    m.add("InferenceObjective", "MaaS", ["poolRef: InferencePool"], "maas")
    bottom = m.close()
    f.rail(svc, [route, pool, epp])
    f.rail(route, [trlp], "warn")

    g = Lane(f, "G", "Gateway namespace")
    gw = g.add("Gateway", "network admin", ["implemented by Istio"])
    ap = g.add("AuthPolicy", "MaaS", ["targetRef: the Gateway"], "maas", 1)
    g.add("TokenRateLimitPolicy", "MaaS", ["default deny, targetRef: Gateway"], "maas")
    g.add("praxis-extproc", "AGC", ["placed by status.gatewayRef"], "agc")
    g.close()
    f.rail(gw, [ap])

    # references
    f.line([left(ref, 92), right(ten, 92)])
    f.pill(330, 92, "tenantRef")
    f.line([right(sub), (300, sub[1] + sub[3] / 2)], head=False)
    f.line([right(auth), (300, auth[1] + auth[3] / 2), (300, 124), left(ref, 124)])
    f.pill(352, 124, "modelRefs")
    f.line([(200, 78), (200, 30), (960, 30), (960, 78)])
    f.pill(580, 30, "spec.gateway")
    f.line([right(route, route[1] + 38), (745, route[1] + 38), (745, 105), left(gw, 105)])
    f.pill(689, route[1] + 38, "parentRefs")
    # MaaS resolves the MaaSModelRef from the route, without a reference between the two
    f.line([right(ref, 113), (692, 113), (692, route[1] + 14), right(route, route[1] + 14)], "warn", dash=True)
    f.pill(692, 176, "MaaS reads", "warn")
    f.h = bottom + 16
    f.legend([
        ("tile", "", "user or admin"),
        ("tile", "ks", "KServe"),
        ("tile", "maas", "MaaS"),
        ("tile", "agc", "AGC"),
        ("rail", "", "owned through an ownerReference"),
        ("line", "", "reference held in a field"),
        ("dash", "", "controller action, no reference"),
        ("line", "warn", "red: listed as a shortcoming"),
        ("group", "", "namespace"),
    ])
    return f


def praxis_lane(f):
    """The right lane of both options. Returns the box of the Praxis proxy tile."""
    g = Lane(f, "G", "Praxis data plane")
    g.add("Platform ingress", "platform", ["forwards to the Praxis Service"])
    px = g.add("Praxis proxy", "gateway-controller", ["rendered from Proxy and Policy"], "gc")
    g.add("Routing config", "gateway-controller", ["from the ModelProviders,", "grouped by publishedName"], "gc")
    g.close()
    return px


@figure("relationships-option-1", "Custom resources in option 1, where KServe creates the ModelProvider")
def relationships_option_1():
    f = RelFig("r2", 1040, 540,
               "Custom resources in option 1. KServe creates the ModelProvider in the tenant namespace, next to "
               "the Proxy and the Policy that MaaS creates. The provider references the AITenant and the "
               "InferencePool, and MaaS sets its status.proxyRef. No ownerReference links the provider to the "
               "LLMInferenceService, and the service needs a reference to the tenant that is not defined.")
    t = Lane(f, "T", "Tenant namespace")
    ten = t.add("AITenant", "platform admin", ["maps the tenant to its Proxy"])
    t.add("MaaSSubscription", "admin", ["input to the Policy, undefined"])
    t.add("MaaSAuthPolicy", "admin", ["input to the Policy, undefined"])
    t.add("Proxy", "MaaS", ["policy slot: the Policy", "routing slot: gateway-controller"], "maas")
    t.add("Policy", "MaaS", ["auth and token limits"], "maas")
    mp = t.add("ModelProvider", "KServe",
               ["aiTenantRef: AITenant", "backend.inferencePoolRef: pool", "status.proxyRef: set by MaaS"], "ks")
    bottom = t.close()

    m = Lane(f, "M", "Model namespace")
    m.add("MaaSModelRef", "user", ["not used to create the provider"])
    svc = m.add("LLMInferenceService", "user", ["needs a reference to the tenant"])
    pool = m.add("InferencePool", "KServe", ["endpointPickerRef: EPP Service"], "ks", 1)
    epp = m.add("EPP, workload", "KServe", ["Deployments and Services"], "ks", 1)
    m.close()
    f.rail(svc, [pool, epp])

    px = praxis_lane(f)

    sy = svc[1]
    f.line([left(svc, sy + 20), (360, sy + 20), (360, 105), right(ten, 105)], "warn", dash=True)
    f.pill(307, 105, "tenant", "warn")
    f.line([left(svc, sy + 38), (314, sy + 38), (314, mp[1] + 16), right(mp, mp[1] + 16)], "warn", dash=True)
    f.pill(314, 300, "KServe creates", "warn")
    py = pool[1] + pool[3] / 2
    f.line([right(mp, mp[1] + 60), (352, mp[1] + 60), (352, py), left(pool, py)])
    f.pill(352, 380, "backend")
    f.line([left(px), (710, px[1] + px[3] / 2), (710, py + 8), right(pool, py + 8)], dash=True)
    f.pill(710, 205, "routes to")
    f.h = bottom + 16
    f.legend([
        ("tile", "", "user or admin"),
        ("tile", "ks", "KServe"),
        ("tile", "maas", "MaaS"),
        ("tile", "gc", "gateway-controller"),
        ("rail", "", "owned through an ownerReference"),
        ("line", "", "reference held in a field"),
        ("dash", "", "controller action, no reference"),
        ("line", "warn", "red: listed as a shortcoming"),
        ("group", "", "namespace"),
    ])
    return f


@figure("relationships-option-2", "Custom resources in option 2, where MaaS creates the ModelProvider")
def relationships_option_2():
    f = RelFig("r3", 1040, 540,
               "Custom resources in option 2. KServe writes only in the model namespace and publishes the backend "
               "in the LLMInferenceService status. MaaS creates the ModelProvider for each MaaSModelRef in the "
               "tenant namespace, next to the Proxy and the Policy. The provider references its backend in the "
               "model namespace.")
    t = Lane(f, "T", "Tenant namespace")
    ten = t.add("AITenant", "platform admin", ["maps the tenant to its Proxy"])
    sub = t.add("MaaSSubscription", "admin", ["token limits per model"])
    auth = t.add("MaaSAuthPolicy", "admin", ["who may call which model"])
    t.add("Proxy", "MaaS", ["policy slot: the Policy", "routing slot: gateway-controller"], "maas")
    t.add("Policy", "MaaS", ["from subscriptions, auth policies"], "maas")
    mp = t.add("ModelProvider", "MaaS", ["backend: pool or Service", "tenant and model ID from MaaS"], "maas")
    bottom = t.close()

    m = Lane(f, "M", "Model namespace")
    ref = m.add("MaaSModelRef", "user", ["modelRef: LLMInferenceService", "cleanup finalizer already exists"])
    svc = m.add("LLMInferenceService", "user", ["status: backend, port,", "model names, Ready"])
    pool = m.add("InferencePool", "KServe", ["endpointPickerRef: EPP Service"], "ks", 1)
    epp = m.add("EPP, workload", "KServe", ["Deployments and Services"], "ks", 1)
    m.add("InferenceObjective", "MaaS", ["poolRef: InferencePool"], "maas")
    m.close()
    f.rail(svc, [pool, epp])

    px = praxis_lane(f)

    f.line([left(ref, 92), right(ten, 92)])
    f.pill(330, 92, "tenantRef")
    f.line([right(sub), (292, sub[1] + sub[3] / 2)], head=False)
    f.line([right(auth), (292, auth[1] + auth[3] / 2), (292, 116), left(ref, 116)])
    f.pill(350, 116, "modelRefs")
    f.line([left(ref, 140), (320, 140), (320, mp[1] + 16), right(mp, mp[1] + 16)], "maas", dash=True)
    f.pill(320, 330, "MaaS creates", "maas")
    py = pool[1] + pool[3] / 2
    f.line([right(mp, mp[1] + 52), (374, mp[1] + 52), (374, py), left(pool, py)])
    f.pill(374, 390, "backend")
    f.line([left(px), (710, px[1] + px[3] / 2), (710, py + 8), right(pool, py + 8)], dash=True)
    f.pill(710, 222, "routes to")
    f.h = bottom + 16
    f.legend([
        ("tile", "", "user or admin"),
        ("tile", "ks", "KServe"),
        ("tile", "maas", "MaaS"),
        ("tile", "gc", "gateway-controller"),
        ("rail", "", "owned through an ownerReference"),
        ("line", "", "reference held in a field"),
        ("dash", "", "controller action, no reference"),
        ("line", "warn", "red: listed as a shortcoming"),
        ("group", "", "namespace"),
    ])
    return f


@figure("relationships-option-3", "Custom resources in the preferred option, where MaaS writes the routing and no ModelProvider exists")
def relationships_option_3():
    f = RelFig("r4", 1040, 540,
               "Custom resources in the preferred option. There is no ModelProvider. MaaS reads the LLMInferenceService "
               "status and writes the routing of each MaaSModelRef inline in the Proxy of the tenant, which "
               "gateway-controller renders. KServe writes only in the model namespace.")
    t = Lane(f, "T", "Tenant namespace")
    ten = t.add("AITenant", "platform admin", ["maps the tenant to its Proxy"])
    sub = t.add("MaaSSubscription", "admin", ["token limits per model"])
    auth = t.add("MaaSAuthPolicy", "admin", ["who may call which model"])
    proxy = t.add("Proxy", "MaaS", ["policy slot: the Policy", "routing: inline, for all models"], "maas")
    t.add("Policy", "MaaS", ["from subscriptions, auth policies"], "maas")
    t_bottom = t.close()

    m = Lane(f, "M", "Model namespace")
    ref = m.add("MaaSModelRef", "user", ["modelRef: LLMInferenceService", "the only object per published model"])
    svc = m.add("LLMInferenceService", "user", ["status: backend, port,", "model names, Ready"])
    pool = m.add("InferencePool", "KServe", ["endpointPickerRef: EPP Service"], "ks", 1)
    epp = m.add("EPP, workload", "KServe", ["Deployments and Services"], "ks", 1)
    m.add("InferenceObjective", "MaaS", ["poolRef: InferencePool"], "maas")
    bottom = max(t_bottom, m.close())
    f.rail(svc, [pool, epp])

    g = Lane(f, "G", "Praxis data plane")
    g.add("Platform ingress", "platform", ["forwards to the Praxis Service"])
    px = g.add("Praxis proxy", "gateway-controller", ["rendered from Proxy and Policy,", "restarts on a routing change"], "gc")
    g.close()

    f.line([left(ref, 92), right(ten, 92)])
    f.pill(330, 92, "tenantRef")
    f.line([right(sub), (292, sub[1] + sub[3] / 2)], head=False)
    f.line([right(auth), (292, auth[1] + auth[3] / 2), (292, 116), left(ref, 116)])
    f.pill(350, 116, "modelRefs")
    f.line([left(ref, 140), (330, 140), (330, proxy[1] + 16), right(proxy, proxy[1] + 16)], "maas", dash=True)
    f.pill(330, 240, "MaaS writes routing", "maas")
    py = pool[1] + pool[3] / 2
    f.line([right(proxy, proxy[1] + 56), (374, proxy[1] + 56), (374, py), left(pool, py)])
    f.pill(374, 292, "backend")
    f.line([left(px), (710, px[1] + px[3] / 2), (710, py + 8), right(pool, py + 8)], dash=True)
    f.pill(710, 225, "routes to")
    f.h = bottom + 16
    f.legend([
        ("tile", "", "user or admin"),
        ("tile", "ks", "KServe"),
        ("tile", "maas", "MaaS"),
        ("tile", "gc", "gateway-controller"),
        ("rail", "", "owned through an ownerReference"),
        ("line", "", "reference held in a field"),
        ("dash", "", "controller action, no reference"),
        ("group", "", "namespace"),
    ])
    return f
