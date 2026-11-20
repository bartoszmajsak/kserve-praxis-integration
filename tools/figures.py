"""The figures, one function each.

A function returns a `Fig` and registers under a name with `@figure`. A page source
places the figure with `<!-- figure: NAME -->`, and the standalone files are
`docs/figs/NAME.svg` and `docs/figs/NAME-dark.svg`.

Encoding of the relationship maps: a tile's colour and header label name who writes the
object, a tile indented under another is owned by it (ownerReference), a solid edge is a
reference held in a field, a dashed edge is a controller acting without a reference, and
red marks a relationship listed as a problem.
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
    f.tile(x, 292, TW, 70, "Routing slot", "from the ModelProviders",
           ["weighted pick by published model name", "then the EPP call, over ext_proc"], accent="warn", icon="route")

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


@figure("modelprovider-ownership", "Ownership of the ModelProvider and the dependencies between the controllers")
def modelprovider_ownership():
    # Every edge runs from the component that acts to the object it acts on.
    f = Fig(
        "f2", 1040, 340,
        "Ownership with MaaS creating the ModelProvider. The KServe controller owns the LLMInferenceService "
        "status and the pool or Service. The MaaS controller reads that status and creates the ModelProvider "
        "next to the MaaSModelRef, the Proxy and the Policy. gateway-controller reads the ModelProvider and "
        "configures the Praxis proxy, which sends requests to the pool or Service. Dependencies run in one "
        "direction.",
    )
    TW = 236
    kx, mx, gx = 28, 402, 776
    f.group(16, 54, 260, 170, "KServe controller")
    f.tile(kx, 78, TW, 70, "LLMInferenceService", "user", ["status: backend, port,", "model names, Ready"], icon="cr")
    f.tile(kx, 156, TW, 54, "Pool or Service", "KServe creates", ["InferencePool, EPP, pods"], icon="pool")

    f.group(390, 54, 260, 232, "MaaS controller")
    f.tile(mx, 78, TW, 70, "ModelProvider", "MaaS creates", ["backend, model ID and tenant", "written by MaaS only"],
           accent="px", icon="cr")
    f.tile(mx, 156, TW, 54, "MaaSModelRef", "user", ["names the service and the tenant"], icon="cr")
    f.tile(mx, 218, TW, 54, "Proxy, Policy", "MaaS creates", ["one per tenant"], icon="hex")

    f.group(764, 54, 260, 170, "Praxis")
    f.tile(gx, 78, TW, 70, "gateway-controller", None, ["reads providers, Proxy, Policy", "renders the proxy config"], icon="ctrl")
    f.tile(gx, 156, TW, 54, "Praxis proxy", None, ["routes on the published model name"], icon="hex")

    f.edge([(390, 113), (kx + TW, 113)], accent="px")
    f.pill(327, 113, "reads status", "px")
    f.edge([(gx, 113), (mx + TW, 113)])
    f.pill(707, 113, "reads")
    f.edge([(gx + TW / 2, 210), (gx + TW / 2, 316), (kx + TW / 2, 316), (kx + TW / 2, 210)], dash=True)
    f.pill(520, 316, "sends requests to")
    f.legend([
        ("line", "px", "MaaS reads the status, in place of the HTTPRoute lookup"),
        ("line", "", "a controller reads the object it points at"),
        ("dash", "", "request path"),
        ("tile", "px", "written by MaaS only"),
        ("group", "", "objects managed by one controller"),
        (None, "", "label on the right of a tile: who writes it"),
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
        ("line", "warn", "red: listed as a problem"),
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
        ("line", "warn", "red: listed as a problem"),
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
        ("line", "warn", "red: listed as a problem"),
        ("group", "", "namespace"),
    ])
    return f


@figure("relationships-option-3", "Custom resources in option 3, where MaaS writes the routing and no ModelProvider exists")
def relationships_option_3():
    f = RelFig("r4", 1040, 540,
               "Custom resources in option 3. There is no ModelProvider. MaaS reads the LLMInferenceService "
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
