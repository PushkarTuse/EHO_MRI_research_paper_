"""Seeded, evaluation-budgeted continuous search implementations.

These are NEW reference implementations, not recovered historical MRI code.
`original_eho` is a bounded continuous implementation of clan attraction,
matriarch-to-centre updating and worst-member separation (Wang et al.,
Elephant Herding Optimization, doi:10.1109/ISCBI.2015.8). It is not a bitwise
reproduction of the authors' software. Uniform separation is strictly within
the continuous box (no integer '+1' range extension), and all proposals clip.

`modified_eho` is an explicitly reconstructed draft hypothesis: D^-gamma,
declining attraction, increasing repulsion and rank-based poor-member
interpolation. Missing numerical choices are exposed in config, not claimed
historical settings. `acor` is an ACOR-inspired archive/Gaussian baseline,
not the manuscript's pheromone-shift code or the discrete ACS algorithm.

All objective calls, including initialization and separation, consume the
budget. Every returned incumbent is a copied actually evaluated position.
History records (cumulative evaluations, best value) after EVERY call.
"""
from __future__ import annotations

from time import perf_counter
import numpy as np

METHODS = ('original_eho', 'modified_eho', 'pso', 'ga', 'acor')


class _BudgetExhausted(Exception):
    pass


class _Evaluator:
    def __init__(self, fun, max_evals):
        self.fun = fun
        self.max_evals = int(max_evals)
        self.evaluations = 0
        self.best_x = None
        self.best = np.inf
        self.history = []
        self.nonfinite = 0

    def __call__(self, x):
        if self.evaluations >= self.max_evals:
            raise _BudgetExhausted
        candidate = np.asarray(x, dtype=float).copy()
        value = float(self.fun(candidate.copy()))
        self.evaluations += 1
        if not np.isfinite(value):
            value = np.inf
            self.nonfinite += 1
        if self.best_x is None or value < self.best:
            self.best, self.best_x = value, candidate
        self.history.append((self.evaluations, float(self.best)))
        return value


def optimise(fun, bounds, method, seed, max_evals=3000, population=30,
             **options):
    """Minimise ``fun(x)`` on finite ``[(lower,upper), ...]`` bounds.

    Returns x, fun, history, evaluations, seconds, method, seed, config and
    provenance. `x` is an independent ndarray. Timing includes initialization
    and Python objective/history overhead, excludes caller I/O and metrics.

    EHO options: clans=5, alpha=.5, beta_center=.1, gamma=.5,
    alpha_min=.05, repulsion_max=.3. Modified flags dimensional_scaling,
    scheduling, repulsion, interpolated_separation default True and support
    declared ablations; original_eho always uses the reference operators.
    PSO: inertia=.7298, cognitive=social=1.49618. GA: mutation_sigma=.1,
    mutation_probability=1/D. ACOR: archive_q=.5, archive_xi=.85.
    All are prespecified defaults, not tuned against these test outcomes.
    """
    start = perf_counter()
    bounds = np.asarray(bounds, dtype=float)
    if bounds.ndim != 2 or bounds.shape[1] != 2 or not len(bounds):
        raise ValueError('bounds must have shape (D,2) with D>=1')
    lo, hi = bounds[:, 0], bounds[:, 1]
    if not np.isfinite(bounds).all() or np.any(hi <= lo):
        raise ValueError('bounds must be finite with upper>lower')
    if method not in METHODS:
        raise ValueError(f'Unknown method {method}; choose {METHODS}')
    if int(max_evals) != max_evals or max_evals < 1:
        raise ValueError('max_evals must be a positive integer')
    if int(population) != population or population < 4:
        raise ValueError('population must be an integer >=4')
    d, width = len(lo), hi-lo
    n = min(int(population), int(max_evals))
    rng = np.random.default_rng(seed)
    ev = _Evaluator(fun, max_evals)
    config = dict(population=int(population), effective_initial_population=n,
                  max_evals=int(max_evals), bounds=bounds.tolist(), options=options)
    clip = lambda x: np.clip(x, lo, hi)
    X = rng.uniform(lo, hi, size=(n, d))
    values = np.array([ev(x) for x in X])
    try:
        if method in ('original_eho', 'modified_eho'):
            c = min(int(options.get('clans', 5)), max(1, n//2))
            if c < 1:
                raise ValueError('clans must be positive')
            clans = np.array_split(np.arange(n), c)
            alpha = float(options.get('alpha', .5))
            beta_center = float(options.get('beta_center', .1))
            gamma = float(options.get('gamma', .5))
            alpha_min = float(options.get('alpha_min', .05))
            repulsion_max = float(options.get('repulsion_max', .3))
            if not (0 <= alpha_min <= alpha <= 1 and 0 <= beta_center <= 1
                    and gamma >= 0 and 0 <= repulsion_max <= 1):
                raise ValueError('Invalid EHO coefficients')
            config.update(clans=c, alpha=alpha, beta_center=beta_center,
                          gamma=gamma, alpha_min=alpha_min,
                          repulsion_max=repulsion_max,
                          dimensional_scaling=method=='modified_eho' and bool(options.get('dimensional_scaling',True)),
                          scheduling=method=='modified_eho' and bool(options.get('scheduling',True)),
                          repulsion=method=='modified_eho' and bool(options.get('repulsion',True)),
                          interpolated_separation=method=='modified_eho' and bool(options.get('interpolated_separation',True)))
            while True:
                # Frozen source positions make each clan update simultaneous.
                old = X.copy()
                old_values = values.copy()
                progress = (ev.evaluations-n)/max(1, max_evals-n)
                modified = method == 'modified_eho'
                scheduled = modified and config['scheduling']
                a = max(alpha_min, alpha*(1-progress)) if scheduled else alpha
                scale = d**(-gamma) if modified and config['dimensional_scaling'] else 1.
                repulse = (repulsion_max*progress if scheduled else repulsion_max)
                if not modified or not config['repulsion']:
                    repulse = 0.
                for clan in clans:
                    leader = clan[np.argmin(old_values[clan])]
                    worst = clan[np.argmax(old_values[clan])]
                    centre = old[clan].mean(axis=0)
                    for i in clan:
                        if i == leader:
                            proposal = beta_center*centre
                        else:
                            proposal = old[i] + a*scale*rng.random()*(old[leader]-old[i])
                            if repulse:
                                proposal -= repulse*rng.random()*(old[worst]-old[i])
                        proposal = clip(proposal)
                        value = ev(proposal)
                        X[i], values[i] = proposal, value
                # Rank after clan update. Separation has its own counted call.
                separation_source = X.copy()
                for clan in clans:
                    worst = clan[np.argmax(values[clan])]
                    if modified and config['interpolated_separation']:
                        partner = int(rng.integers(n))
                        proposal = X[worst]+rng.random()*(separation_source[partner]-X[worst])
                    else:
                        proposal = rng.uniform(lo,hi)
                    proposal = clip(proposal)
                    value = ev(proposal)
                    X[worst],values[worst] = proposal,value
        elif method == 'pso':
            w = float(options.get('inertia', .7298))
            c1 = float(options.get('cognitive', 1.49618))
            c2 = float(options.get('social', 1.49618))
            config.update(inertia=w,cognitive=c1,social=c2)
            velocity = rng.uniform(-.1*width,.1*width,size=(n,d))
            personal, personal_f = X.copy(),values.copy()
            while True:
                guide = ev.best_x.copy()
                for i in range(n):
                    velocity[i] = (w*velocity[i]+c1*rng.random(d)*(personal[i]-X[i])
                                   +c2*rng.random(d)*(guide-X[i]))
                    trial = X[i]+velocity[i]
                    hit = (trial < lo)|(trial > hi)
                    trial = clip(trial)
                    velocity[i,hit] = 0.
                    value = ev(trial)
                    X[i],values[i] = trial,value
                    if value < personal_f[i]:
                        personal[i],personal_f[i] = trial.copy(),value
        elif method == 'ga':
            sigma = float(options.get('mutation_sigma', .1))
            prob = float(options.get('mutation_probability',1/d))
            config.update(tournament=3,mutation_sigma=sigma,mutation_probability=prob,
                          crossover='coordinatewise convex arithmetic',elite_survival='mu plus lambda')
            while True:
                children, costs = [], []
                for _ in range(n):
                    parents = []
                    for __ in range(2):
                        tournament = rng.integers(n,size=3)
                        parents.append(X[tournament[np.argmin(values[tournament])]])
                    mix = rng.random(d)
                    child = mix*parents[0]+(1-mix)*parents[1]
                    mask = rng.random(d)<prob
                    child += mask*rng.normal(0,sigma*width,d)
                    child = clip(child)
                    costs.append(ev(child));children.append(child)
                union=np.vstack((X,children));f=np.r_[values,costs]
                idx=np.argsort(f,kind='stable')[:n]
                X,values=union[idx].copy(),f[idx].copy()
        else:
            q=float(options.get('archive_q',.5));xi=float(options.get('archive_xi',.85))
            if q<=0 or xi<=0:
                raise ValueError('ACOR q and xi must be positive')
            config.update(archive_q=q,archive_xi=xi,archive_size=n,
                          sampling='one ranked archive kernel per candidate',sigma_floor_relative=1e-12)
            while True:
                order=np.argsort(values,kind='stable');X,values=X[order],values[order]
                rank=np.arange(n);weights=np.exp(-rank**2/(2*(q*n)**2));weights/=weights.sum()
                children,costs=[],[]
                for _ in range(n):
                    k=int(rng.choice(n,p=weights))
                    sigma=xi*np.abs(X-X[k]).sum(axis=0)/max(1,n-1)
                    sigma=np.maximum(sigma,1e-12*width)
                    child=clip(rng.normal(X[k],sigma))
                    costs.append(ev(child));children.append(child)
                union=np.vstack((X,children));f=np.r_[values,costs]
                keep=np.argsort(f,kind='stable')[:n]
                X,values=union[keep].copy(),f[keep].copy()
    except _BudgetExhausted:
        pass
    return dict(x=ev.best_x.copy(), fun=float(ev.best),history=ev.history,
                evaluations=ev.evaluations,seconds=perf_counter()-start,
                method=method,seed=int(seed),config=config,
                nonfinite_evaluations=ev.nonfinite,
                provenance=('reconstructed draft operator hypothesis' if method=='modified_eho'
                            else 'new bounded literature-aligned reference implementation' if method=='original_eho'
                            else 'new ACOR-inspired continuous archive baseline' if method=='acor'
                            else 'new prespecified continuous baseline'))
