"""Verify shared benchmark accounting and incumbent consistency, not rankings."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from optimizers import METHODS, optimise
from benchmarks_continuous import ackley, rastrigin
from ablations import TASKS,shifted_objective,VARIANTS


@pytest.mark.parametrize('fun',[ackley,rastrigin])
def test_known_zero_optimum(fun):
    assert abs(fun(np.zeros(10)))<1e-12
    assert fun(np.ones(10)*.33)>0


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.parametrize('budget',[1,29,30,31,63])
def test_exact_calls_and_actual_best_position(method,budget):
    calls=[]
    def objective(x):
        assert np.all(x>=-2) and np.all(x<=3)
        value=float(np.sum((x-.7)**2))
        calls.append((x.copy(),value))
        return value
    result=optimise(objective,[(-2,3)]*3,method,11,max_evals=budget,population=30)
    assert len(calls)==result['evaluations']==budget
    assert len(result['history'])==budget
    assert [h[0] for h in result['history']]==list(range(1,budget+1))
    incumbent=np.array([h[1] for h in result['history']])
    assert np.all(np.diff(incumbent)<=0)
    assert result['fun']==min(v for _,v in calls)
    assert result['fun']==float(np.sum((result['x']-.7)**2))
    assert any(np.array_equal(result['x'],x) for x,v in calls if v==result['fun'])
    assert not np.shares_memory(result['x'],calls[0][0])


@pytest.mark.parametrize('method',METHODS)
def test_seed_reproducibility(method):
    a=optimise(rastrigin,[(-5.12,5.12)]*4,method,6,max_evals=100)
    b=optimise(rastrigin,[(-5.12,5.12)]*4,method,6,max_evals=100)
    assert np.array_equal(a['x'],b['x']) and a['history']==b['history']


@pytest.mark.parametrize('method',METHODS)
def test_nonfinite_objective_is_counted(method):
    result=optimise(lambda x:np.nan,[(-1,1)]*2,method,5,max_evals=35)
    assert result['evaluations']==result['nonfinite_evaluations']==35
    assert np.isinf(result['fun'])
    assert np.isfinite(result['x']).all()


@pytest.mark.parametrize('bounds',[[[0,0]],[[1,0]],[[0,np.inf]],[]])
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError):
        optimise(rastrigin,bounds,'modified_eho',0)


@pytest.mark.parametrize('task',TASKS)
def test_prespecified_shifted_optimum(task):
    base,limit,shift=TASKS[task]
    assert shift.shape==(10,) and np.all(np.abs(shift)<limit)
    assert abs(shifted_objective(shift,base,shift))<1e-12
    assert shifted_objective(np.zeros(10),base,shift)>0


@pytest.mark.parametrize('variant',VARIANTS)
def test_ablation_budget_and_effective_flags(variant):
    method,flags=VARIANTS[variant]
    result=optimise(rastrigin,[(-5.12,5.12)]*4,method,0,max_evals=65,**flags)
    assert result['evaluations']==65
    for flag,value in flags.items():assert result['config'][flag]==value
    if method=='original_eho':
        assert not any(result['config'][flag] for flag in ['dimensional_scaling','scheduling','repulsion','interpolated_separation'])
