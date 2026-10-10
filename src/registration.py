"""Separate legacy synthetic registration and matched-budget registration.

Synthetic data/warp match the notebook: seed-42 uniform field, 25-degree
rotation followed by integer circular shifts (5,-3), full-array MSE. The new
matched comparison corrects budgeting and optimizer implementations, NOT that
legacy image model. Its outcome is not anatomical or diagnostic accuracy.

Optional --anatomical PATH creates a distinct, known-transform experiment from
one MRI slice with continuous affine interpolation, constant boundaries and a
fixed conservative interior foreground mask. Truth is a pull mapping from the
fixed grid to the moving grid; the moving image is generated with its inverse.
This is single-case synthetic perturbation of anatomy, not patient registration.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.ndimage import rotate, affine_transform, zoom
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from optimizers import METHODS, optimise
from benchmarks_continuous import (BASE,load_notebook_definitions,measured_source_call,
                                  save_json,save_run,summarize)


def legacy_transform(image,params):
    angle,tx,ty=params
    return np.roll(rotate(image,float(angle),reshape=False,order=1),
                   shift=(int(tx),int(ty)),axis=(0,1))


def affine_parameters(shape,params):
    """Pull map y=M*x+b in row/column pixel coordinates; angle in degrees."""
    angle,tx,ty=np.asarray(params,float)
    theta=np.deg2rad(angle)
    matrix=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
    centre=(np.asarray(shape)-1)/2
    offset=centre+np.array([tx,ty])-matrix@centre
    return matrix,offset


def rigid_warp(image,params):
    matrix,offset=affine_parameters(image.shape,params)
    return affine_transform(image,matrix,offset,order=1,mode='constant',cval=0.,prefilter=False)


def make_anatomical_case(path,slice_index=71,max_size=128,modality=0):
    """Create image-only rigid registration from 3D data or one 4D channel.

    For Task01_BrainTumour, modality 0 is FLAIR according to dataset.json.
    The reference segmentation is never loaded or used by this procedure.
    """
    import nibabel as nib
    image=nib.load(str(path));native_shape=list(image.shape)
    if len(image.shape)==4:
        if not 0<=modality<image.shape[3]:
            raise ValueError('modality must select a valid 4D channel')
        # Read just the chosen channel rather than allocating all four volumes.
        volume=np.asarray(image.dataobj[:,:,:,modality],dtype=np.float32)
    else:
        volume=np.asarray(image.dataobj,dtype=np.float32)
    if volume.ndim!=3 or not 0<=slice_index<volume.shape[2]:
        raise ValueError('Anatomical input must be a 3D/4D NIfTI with valid axis-2 slice')
    if max_size<32:
        raise ValueError('max_size must be >=32 for the fixed translation range')
    fixed=volume[:,:,slice_index].astype(float)
    positive=fixed[fixed>0]
    if positive.size<20:raise ValueError('Selected slice lacks nonzero anatomical content')
    # Declared reproducible scaling; no labels or test outcomes determine it.
    high=float(np.percentile(positive,99.5))
    fixed=np.clip(fixed/high,0,1)
    factor=min(1.,max_size/max(fixed.shape))
    if factor<1:fixed=zoom(fixed,factor,order=1,prefilter=False)
    truth=np.array([12.,4.,-3.])
    matrix,offset=affine_parameters(fixed.shape,truth)
    inv=np.linalg.inv(matrix)
    moving=affine_transform(fixed,inv,-inv@offset,order=1,mode='constant',cval=0.,prefilter=False)
    bounds=np.array([[-30.,30.],[-12.,12.],[-12.,12.]])
    rr,cc=np.indices(fixed.shape);centre=(np.asarray(fixed.shape)-1)/2
    radius=min(centre)-np.sqrt(2)*12-2
    if radius<=3:raise ValueError('Image too small for prespecified translation range')
    interior=(rr-centre[0])**2+(cc-centre[1])**2<=radius**2
    mask=interior&(fixed>0)
    if mask.sum()<20:raise ValueError('Insufficient fixed interior foreground support')
    # These landmarks are geometric grid points, NOT annotated anatomical landmarks.
    r=radius/2
    landmarks=np.array([centre,centre+[r,0],centre+[-r,0],centre+[0,r],centre+[0,-r]])
    metadata=dict(path=str(Path(path).resolve()),slice_index=int(slice_index),slice_axis=2,
                  native_shape=native_shape,selected_volume_shape=list(volume.shape),
                  modality_index=int(modality) if len(native_shape)==4 else None,
                  modality_note='Task01_BrainTumour channel 0 is FLAIR; channel names depend on input dataset',
                  evaluation_shape=list(fixed.shape),
                  resize_factor=factor,positive_percentile_99_5=high,nifti_affine=image.affine.tolist(),
                  truth_pull_parameters=truth.tolist(),pixel_mask_count=int(mask.sum()),
                  fixed_mask='circular interior safe for bounds, intersected with fixed>0',
                  intensity_normalisation='clip(raw / positive-pixel 99.5th percentile,0,1)',
                  limitation='single anatomical slice with synthetic rigid perturbation; no independent patient cohort')
    return fixed,moving,bounds,truth,mask,landmarks,metadata


def geometric_error(shape,estimate,truth,landmarks):
    me,be=affine_parameters(shape,estimate);mt,bt=affine_parameters(shape,truth)
    error=(landmarks@me.T+be)-(landmarks@mt.T+bt)
    return float(np.sqrt(np.mean(np.sum(error**2,axis=1))))


def save_alignment(out,task,method,seed,fixed,moving,aligned,mask=None):
    # Only seed zero figures; arrays for every measured run are retained separately.
    if seed!=0:return
    fig,axs=plt.subplots(1,4,figsize=(12,3))
    for ax,data,title in zip(axs,[fixed,moving,aligned,np.abs(fixed-aligned)],
                             ['Reference','Moving','Aligned','Absolute residual']):
        ax.imshow(data,cmap='gray',vmin=0,vmax=1);ax.set_title(title);ax.axis('off')
    fig.suptitle(f'{task}: {method}; seed {seed}',fontsize=10)
    fig.tight_layout();fig.savefig(Path(out)/f'{task}__{method}__seed{seed}.png',dpi=160);plt.close(fig)


def run_source(out,seeds,notebook):
    fixed=np.random.RandomState(42).rand(100,100)
    moving=legacy_transform(fixed,[25,5,-3]);bounds=[(-45,45),(-20,20),(-20,20)]
    rows=[]
    for seed in seeds:
        for method in ['pso','eho','ga','aco']:
            ns,provenance=load_notebook_definitions(notebook,15)
            def invoke(namespace):
                fn=namespace[f'{method}_registration']
                if method=='eho':return fn(fixed,moving,30,5,50,bounds)
                return fn(fixed,moving,30,50,bounds)
            result=measured_source_call(ns,'objective_function',invoke,seed)
            result['returned_x_objective']=float(ns['objective_function'](result['x'],fixed,moving))
            result['provenance']=provenance
            result['config']=dict(population=30,requested_iterations=50,eho_actual_cap=20,bounds=bounds,
                                  true_forward_source_transform=[25,5,-3],synthetic_seed=42,
                                  transform='rotation linear interpolation then circular int translation')
            rows.append(save_run(out,'synthetic_source_cell15',method,seed,result,'source_unchanged_bodies'))
            save_alignment(out,'synthetic_source_cell15',method,seed,fixed,moving,legacy_transform(moving,result['x']))
            print(f'source registration {method} seed={seed} MSE={result["fun"]:.7g}',flush=True)
    return rows


def run_matched_case(out,task,fixed,moving,bounds,seeds,budget,population,warp,
                     mask=None,truth=None,landmarks=None,metadata=None):
    rows=[]
    if mask is None:mask=np.ones(fixed.shape,bool)
    objective=lambda p:float(np.mean((fixed[mask]-warp(moving,p)[mask])**2))
    baseline=float(np.mean((fixed[mask]-moving[mask])**2))
    save_json(Path(out)/f'{task}_case.json',dict(metadata or {},bounds=np.asarray(bounds).tolist(),
              unregistered_mse=baseline,true_transform_mse=objective(truth) if truth is not None else None,
              endpoint='MSE on fixed mask',training='none',timing='optimizer plus objective only, excludes loading and report rendering'))
    np.savez_compressed(Path(out)/f'{task}_input.npz',fixed=fixed,moving=moving,mask=mask,
                        truth=np.asarray(truth) if truth is not None else np.empty(0))
    for seed in seeds:
        for method in np.random.default_rng(seed+1981).permutation(METHODS):
            result=optimise(objective,bounds,str(method),seed,max_evals=budget,population=population)
            result['returned_x_objective']=objective(result['x'])
            aligned=warp(moving,result['x'])
            result['unregistered_mse']=baseline
            if truth is not None:
                result['parameter_error']=np.asarray(result['x'])-truth
                result['grid_landmark_rmse_pixels']=geometric_error(fixed.shape,result['x'],truth,landmarks)
                result['geometric_metric_definition']='RMS pull-mapping displacement on five geometric grid landmarks; not clinical TRE'
            row=save_run(out,task,str(method),seed,result,'matched_evaluations')
            if truth is not None:row['grid_landmark_rmse_pixels']=result['grid_landmark_rmse_pixels']
            rows.append(row)
            np.savez_compressed(Path(out)/'raw'/f'{task}__{method}__seed{seed}_aligned.npz',aligned=aligned)
            save_alignment(out,task,str(method),seed,fixed,moving,aligned,mask)
            print(f'{task} {method} seed={seed} MSE={result["fun"]:.7g} evals={result["evaluations"]}',flush=True)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',required=True,type=Path);ap.add_argument('--seeds',default='0,1,2,3,4')
    ap.add_argument('--source-seeds',default='0,1,2');ap.add_argument('--budget',type=int,default=1500)
    ap.add_argument('--population',type=int,default=30);ap.add_argument('--mode',choices=['all','source','matched'],default='all')
    ap.add_argument('--notebook',type=Path,default=BASE/'sources/mri_optimisation.ipynb')
    ap.add_argument('--anatomical',type=Path);ap.add_argument('--slice',type=int,default=71)
    ap.add_argument('--modality',type=int,default=0,help='4D channel; Task01_BrainTumour 0=FLAIR')
    ap.add_argument('--max-size',type=int,default=128)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    save_json(args.output/'protocol.json',vars(args));rows=[]
    if args.mode in ('all','source'):
        rows.extend(run_source(args.output,[int(s) for s in args.source_seeds.split(',')],args.notebook))
    if args.mode in ('all','matched'):
        seeds=[int(s) for s in args.seeds.split(',')]
        fixed=np.random.RandomState(42).rand(100,100);moving=legacy_transform(fixed,[25,5,-3])
        rows.extend(run_matched_case(args.output,'synthetic_legacy_transform',fixed,moving,
            [(-45,45),(-20,20),(-20,20)],seeds,args.budget,args.population,legacy_transform,
            metadata=dict(synthetic_seed=42,source_forward_transform=[25,5,-3],
                limitation='same legacy circular integer translation and full-array metric; not anatomical validation')))
        if args.anatomical:
            fixed,moving,bounds,truth,mask,points,metadata=make_anatomical_case(args.anatomical,args.slice,args.max_size,args.modality)
            rows.extend(run_matched_case(args.output,'anatomical_rigid_perturbation',fixed,moving,bounds,
                seeds,args.budget,args.population,rigid_warp,mask,truth,points,metadata))
    summarize(args.output,rows)
    geometric=[r for r in rows if 'grid_landmark_rmse_pixels' in r]
    if geometric:
        import pandas as pd
        pd.DataFrame(geometric).groupby('method').grid_landmark_rmse_pixels.agg(['count','mean','std']).to_csv(args.output/'anatomical_geometry_summary.csv')


if __name__=='__main__':main()
