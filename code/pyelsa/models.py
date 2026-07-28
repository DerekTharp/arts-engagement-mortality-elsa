"""Estimators used across the pipeline, implemented in numpy/scipy so the
whole engine depends only on numpy, scipy and pandas.

Each estimator reproduces the corresponding Stata command:
  cox_ph        -> stcox (Breslow ties, age timescale via left truncation),
                   model-based or vce(cluster) SEs
  glm_cloglog   -> cloglog with offset(), optional pweight, vce(cluster)
  logit_glm     -> logit
  mnlogit       -> mlogit (predicted probabilities)
  ologit        -> ologit (proportional-odds; coef + SE)
  ols           -> regress (coef + SE)

Cluster-robust variance uses the standard sandwich with the Stata small-sample
scaling G/(G-1), verified against the committed Stata output CSVs.
"""
import numpy as np
from scipy.optimize import minimize


# ===========================================================================
# Cox proportional hazards (Breslow ties, left truncation)
# ===========================================================================
def _cox_prep(X, entry, exit_, event):
    et = np.unique(exit_[event])                       # unique event times
    R = (entry[None, :] < et[:, None]) & (et[:, None] <= exit_[None, :])
    D = event[None, :] & (exit_[None, :] == et[:, None])
    dcount = D.sum(1).astype(float)
    return et, R, D, dcount


def _cox_negll(beta, X, R, D, dcount):
    eta = X @ beta
    ee = np.exp(eta)
    s0 = R @ ee
    return -((D @ eta) - dcount * np.log(s0)).sum()


def _cox_grad(beta, X, R, D, dcount):
    eta = X @ beta
    ee = np.exp(eta)
    s0 = R @ ee
    s1 = (R * ee[None, :]) @ X
    xbar = s1 / s0[:, None]
    return -((D @ X).sum(0) - (dcount[:, None] * xbar).sum(0))


def _cox_info(beta, X, R, D, dcount):
    """Observed information matrix (negative Hessian of the Breslow partial
    log-likelihood), vectorised: info = X' diag(wn) X - sum_k d_k xbar_k xbar_k',
    with wn_i = w_i * sum_k (d_k/S0_k) R_{k,i}."""
    ee = np.exp(X @ beta)
    s0 = R @ ee
    s1 = (R * ee[None, :]) @ X
    xbar = s1 / s0[:, None]
    wn = ee * (R.T @ (dcount / s0))
    return (X.T * wn) @ X - (xbar * dcount[:, None]).T @ xbar


def _cox_score_residuals(beta, X, entry, exit_, event, et, R, D, dcount):
    """Per-subject score (efficient) residuals for the robust/cluster sandwich
    (Lin & Wei), Breslow version."""
    n, p = X.shape
    eta = X @ beta
    ee = np.exp(eta)
    s0 = R @ ee
    s1 = (R * ee[None, :]) @ X
    xbar = s1 / s0[:, None]                         # (k,p)
    # First term: delta_i (x_i - xbar_{t_i}) for events.
    U = np.zeros((n, p))
    # map each subject's event time (if event) to the index in et
    et_index = {t: i for i, t in enumerate(et)}
    for i in np.where(event)[0]:
        k = et_index[exit_[i]]
        U[i] += X[i] - xbar[k]
    # Second term: -sum_k (in i's at-risk set) (w_i/s0_k)(x_i - xbar_k) dcount_k
    # R[k,i] marks subject i at risk at event time k.
    w_over_s0 = (R * ee[None, :]) / s0[:, None]      # (k,n): w_i/s0_k if at risk
    # contribution to subject i: sum_k w_over_s0[k,i] * dcount_k * (x_i - xbar_k)
    coef = w_over_s0 * dcount[:, None]               # (k,n)
    U -= X * coef.sum(0)[:, None]                    # sum_k coef * x_i
    U += coef.T @ xbar                               # + sum_k coef * xbar_k
    return U


def cox_ph(X, entry, exit_, event, cluster=None, se=True, init=None):
    """Fit Cox PH (Breslow, left truncation) by Newton-Raphson. Returns dict
    with beta, and (if se) se/cov plus n, n_events. cluster: ids for
    vce(cluster); None with se gives model-based SEs. init warm-starts beta."""
    X = np.asarray(X, float)
    entry = np.asarray(entry, float)
    exit_ = np.asarray(exit_, float)
    event = np.asarray(event, bool)
    et, R, D, dcount = _cox_prep(X, entry, exit_, event)
    p = X.shape[1]
    beta = np.zeros(p) if init is None else np.asarray(init, float).copy()
    for _ in range(50):
        g = _cox_grad(beta, X, R, D, dcount)
        info = _cox_info(beta, X, R, D, dcount)
        step = np.linalg.solve(info, g)
        beta = beta - step
        if np.max(np.abs(step)) < 1e-9:
            break
    if not se:
        return {"beta": beta, "n": X.shape[0], "n_events": int(event.sum())}
    info = _cox_info(beta, X, R, D, dcount)
    inv_info = np.linalg.inv(info)
    if cluster is None:
        cov = inv_info
    else:
        U = _cox_score_residuals(beta, X, entry, exit_, event, et, R, D, dcount)
        cluster = np.asarray(cluster)
        meat = np.zeros((p, p))
        for g in np.unique(cluster):
            ug = U[cluster == g].sum(0)
            meat += np.outer(ug, ug)
        G = len(np.unique(cluster))
        meat *= G / (G - 1.0)
        cov = inv_info @ meat @ inv_info
    return {"beta": beta, "se": np.sqrt(np.diag(cov)), "cov": cov,
            "n": X.shape[0], "n_events": int(event.sum())}


def cox_beta_fast(X, entry, exit_, event, init=None, tol=1e-9, maxit=50):
    """Beta-only Breslow Cox by full Newton-Raphson, using the counting-process
    identity (risk-set sum over entry < t <= exit = reverse cumsum over exit>=t
    minus over entry>=t) for S0/S1, and a per-subject range-sum for the
    information matrix, so no O(events x n) risk matrix or O(n*p*p) array is
    formed. Returns the exact MLE beta; SEs are not computed (not needed for the
    undercount simulation). Matches cox_ph beta to machine precision."""
    X = np.asarray(X, float)
    entry = np.asarray(entry, float)
    exit_ = np.asarray(exit_, float)
    event = np.asarray(event, bool)
    n, p = X.shape
    ut, inv = np.unique(exit_[event], return_inverse=True)
    dcount = np.bincount(inv, minlength=len(ut)).astype(float)
    Dxsum = X[event].sum(0)
    exo = np.argsort(exit_, kind="mergesort")
    eno = np.argsort(entry, kind="mergesort")
    jA = np.searchsorted(exit_[exo], ut, side="left")
    jB = np.searchsorted(entry[eno], ut, side="left")
    # per-subject risk-membership range on the sorted failure times
    hi = np.searchsorted(ut, exit_, side="right")   # #{ut <= exit_i}
    lo = np.searchsorted(ut, entry, side="right")   # #{ut <= entry_i}

    def rcs(a):
        c = np.cumsum(a[::-1], axis=0)[::-1]
        return np.concatenate([c, np.zeros((1,) + a.shape[1:])], axis=0)

    beta = np.zeros(p) if init is None else np.asarray(init, float).copy()
    for _ in range(maxit):
        w = np.exp(X @ beta)
        wx = w[:, None] * X
        S0 = rcs(w[exo])[jA] - rcs(w[eno])[jB]
        S1 = rcs(wx[exo])[jA] - rcs(wx[eno])[jB]
        xbar = S1 / S0[:, None]
        grad = -(Dxsum - (dcount[:, None] * xbar).sum(0))
        # info = X' diag(wn) X - sum_k d_k xbar_k xbar_k', with
        # wn_i = w_i * sum_{k: entry_i < ut_k <= exit_i} dcount_k / S0_k
        c = dcount / S0
        Ccum = np.concatenate([[0.0], np.cumsum(c)])
        wn = w * (Ccum[hi] - Ccum[lo])
        info = (X.T * wn) @ X - (xbar * dcount[:, None]).T @ xbar
        step = np.linalg.solve(info, grad)
        beta = beta - step
        if np.max(np.abs(step)) < tol:
            break
    return beta


# ===========================================================================
# GLM via IRLS: binomial with logit or cloglog link, offset, weights, cluster
# ===========================================================================
def _glm_links(link):
    if link == "logit":
        def mu(eta):
            return 1.0 / (1.0 + np.exp(-eta))

        def dmu(eta):
            m = mu(eta)
            return m * (1 - m)
    elif link == "cloglog":
        def mu(eta):
            return 1.0 - np.exp(-np.exp(np.clip(eta, -30, 30)))

        def dmu(eta):
            e = np.exp(np.clip(eta, -30, 30))
            return e * np.exp(-e)
    else:
        raise ValueError(link)
    return mu, dmu


def glm_binomial(y, X, link="logit", offset=None, weights=None, cluster=None,
                 maxiter=100, tol=1e-10):
    """Binomial GLM by IRLS with an intercept prepended internally. Returns beta
    and se aligned as [intercept, X columns] (model-based if cluster/weights are
    None, else cluster-robust sandwich with G/(G-1) scaling), plus fitted mu.
    weights are probability weights entering the score, matching Stata pweight
    point estimates; pweight always yields robust SEs, so pass cluster."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    X = np.column_stack([np.ones(len(X)), X])       # intercept
    n, p = X.shape
    off = np.zeros(n) if offset is None else np.asarray(offset, float)
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    mu_f, dmu_f = _glm_links(link)

    def nll(beta):
        eta = X @ beta + off
        mu = np.clip(mu_f(eta), 1e-12, 1 - 1e-12)
        return -np.sum(w * (y * np.log(mu) + (1 - y) * np.log(1 - mu)))

    def grad(beta):
        eta = X @ beta + off
        mu = np.clip(mu_f(eta), 1e-12, 1 - 1e-12)
        d = dmu_f(eta)
        v = mu * (1 - mu)
        return -X.T @ (w * (y - mu) * d / v)

    # sensible intercept start: cloglog/logit of the (weighted) event rate
    beta0 = np.zeros(p)
    pbar = np.clip(np.average(y, weights=w), 1e-4, 1 - 1e-4)
    beta0[0] = (np.log(pbar / (1 - pbar)) if link == "logit"
                else np.log(-np.log(1 - pbar))) - np.mean(off)
    res = minimize(nll, beta0, jac=grad, method="BFGS",
                   options={"gtol": 1e-8, "maxiter": 2000})
    beta = res.x
    eta = X @ beta + off
    mu = np.clip(mu_f(eta), 1e-12, 1 - 1e-12)
    d = dmu_f(eta)
    v = mu * (1 - mu)
    if cluster is None and weights is None:
        W = w * d * d / v
        cov = np.linalg.inv((X * W[:, None]).T @ X)   # expected-information (ML)
    else:
        # Robust/cluster sandwich uses the OBSERVED information as the bread
        # (Stata convention). For the non-canonical cloglog link the observed
        # and expected information differ; the observed Hessian is the numerical
        # Jacobian of the score at the MLE.
        eps = 1e-6
        H = np.zeros((p, p))
        g0 = grad(beta)
        for j in range(p):
            bb = beta.copy(); bb[j] += eps
            H[:, j] = (grad(bb) - g0) / eps
        H = 0.5 * (H + H.T)
        bread = np.linalg.inv(H)
        # score contribution per obs: u_i = w_i * (y-mu) d / v * x_i
        s = (w * (y - mu) * d / v)[:, None] * X
        if cluster is None:
            meat = s.T @ s
            cov = bread @ meat @ bread
        else:
            cluster = np.asarray(cluster)
            meat = np.zeros((p, p))
            for g in np.unique(cluster):
                sg = s[cluster == g].sum(0)
                meat += np.outer(sg, sg)
            G = len(np.unique(cluster))
            meat *= G / (G - 1.0)
            cov = bread @ meat @ bread
    return {"beta": beta, "se": np.sqrt(np.diag(cov)), "cov": cov, "n": n,
            "mu": mu}


def logit_glm(y, X, cluster=None):
    return glm_binomial(y, X, link="logit", cluster=cluster)


# ===========================================================================
# Multinomial logit (predicted probabilities; matches mlogit, base = 0)
# ===========================================================================
def mnlogit_fit(X, y, K=3):
    X1 = np.column_stack([np.ones(len(X)), X])
    n, p1 = X1.shape
    Y = np.zeros((n, K)); Y[np.arange(n), y.astype(int)] = 1

    def probs(theta):
        B = theta.reshape(K - 1, p1)
        eta = np.zeros((n, K)); eta[:, 1:] = X1 @ B.T
        eta -= eta.max(1, keepdims=True)
        e = np.exp(eta)
        return e / e.sum(1, keepdims=True)

    def nll(theta):
        return -np.sum(Y * np.log(np.clip(probs(theta), 1e-300, None)))

    def grad(theta):
        return ((probs(theta) - Y)[:, 1:].T @ X1).ravel()

    r = minimize(nll, np.zeros((K - 1) * p1), jac=grad, method="L-BFGS-B",
                 options={"maxiter": 5000, "ftol": 1e-14, "gtol": 1e-10})
    return r.x, p1


def mnlogit_predict(theta, X, p1, K=3):
    X1 = np.column_stack([np.ones(len(X)), X])
    B = theta.reshape(K - 1, p1)
    eta = np.zeros((len(X1), K)); eta[:, 1:] = X1 @ B.T
    eta -= eta.max(1, keepdims=True)
    e = np.exp(eta)
    return e / e.sum(1, keepdims=True)


# ===========================================================================
# Ordered logit (proportional odds); returns coef + SE for the covariates.
# Matches Stata ologit parameterisation (Xb with cutpoints; positive coef =>
# higher category more likely).
# ===========================================================================
def ologit(y, X):
    y = np.asarray(y, int)
    X = np.asarray(X, float)
    cats = np.sort(np.unique(y))
    J = len(cats)
    ymap = {c: i for i, c in enumerate(cats)}
    yi = np.array([ymap[v] for v in y])
    n, p = X.shape

    def unpack(par):
        beta = par[:p]
        # cutpoints strictly increasing via cumulative softplus
        raw = par[p:]
        cuts = np.concatenate([[raw[0]], raw[0] + np.cumsum(np.exp(raw[1:]))])
        return beta, cuts

    def nll(par):
        beta, cuts = unpack(par)
        eta = X @ beta
        # P(y<=j) = sigmoid(cuts_j - eta)
        big = np.concatenate([cuts, [np.inf]])
        low = np.concatenate([[-np.inf], cuts])
        ll = 0.0
        for j in range(J):
            hi = 1.0 / (1.0 + np.exp(-(big[j] - eta))) if np.isfinite(big[j]) else 1.0
            lo = 1.0 / (1.0 + np.exp(-(low[j] - eta))) if np.isfinite(low[j]) else 0.0
            pj = np.clip(hi - lo, 1e-300, None)
            ll += np.log(pj[yi == j]).sum()
        return -ll

    par0 = np.zeros(p + (J - 1))
    par0[p:] = np.linspace(-1, 1, J - 1)
    par0[p + 1:] = 0.0
    r = minimize(nll, par0, method="BFGS", options={"gtol": 1e-8, "maxiter": 5000})
    beta, cuts = unpack(r.x)

    # Standard errors from the observed information in the natural (beta, cuts)
    # parameterisation (BFGS's hess_inv over the softplus params is only
    # approximate). Build the log-likelihood directly in (beta, cuts) and take
    # its numerical Hessian at the MLE.
    def nll_direct(par):
        bb = par[:p]
        cc = par[p:]
        eta = X @ bb
        big = np.concatenate([cc, [np.inf]])
        low = np.concatenate([[-np.inf], cc])
        ll = 0.0
        for j in range(J):
            hi = 1.0 / (1.0 + np.exp(-(big[j] - eta))) if np.isfinite(big[j]) else 1.0
            lo = 1.0 / (1.0 + np.exp(-(low[j] - eta))) if np.isfinite(low[j]) else 0.0
            ll += np.log(np.clip(hi - lo, 1e-300, None))[yi == j].sum()
        return -ll

    theta = np.concatenate([beta, cuts])
    m = len(theta)
    eps = 1e-5
    H = np.zeros((m, m))
    f0 = nll_direct(theta)
    for i in range(m):
        for j in range(i, m):
            ti = theta.copy(); ti[i] += eps; ti[j] += eps
            tj = theta.copy(); tj[i] += eps
            tk = theta.copy(); tk[j] += eps
            H[i, j] = H[j, i] = (nll_direct(ti) - nll_direct(tj) - nll_direct(tk) + f0) / eps ** 2
    cov = np.linalg.inv(H)[:p, :p]
    return {"beta": beta, "se": np.sqrt(np.abs(np.diag(cov)))}


# ===========================================================================
# OLS (regress); coef + classical SE.
# ===========================================================================
def ols(y, X):
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, p = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    sigma2 = (resid @ resid) / (n - p)
    cov = sigma2 * XtX_inv
    return {"beta": beta, "se": np.sqrt(np.diag(cov)), "df_resid": n - p,
            "n": n}


def hr_ci(beta_i, se_i):
    return (np.exp(beta_i), np.exp(beta_i - 1.96 * se_i),
            np.exp(beta_i + 1.96 * se_i))
