"""Check declared pull-map conventions and leakage-free 4D loading."""
from pathlib import Path
import sys
import nibabel as nib
import numpy as np
from scipy.ndimage import affine_transform
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from registration import affine_parameters,rigid_warp,geometric_error,make_anatomical_case


def phantom(n=80):
    r,c=np.indices((n,n));return np.exp(-((r-.4*n)**2+(c-.55*n)**2)/(n*.1)**2)


def test_identity_pull_map():
    image=phantom()
    m,b=affine_parameters(image.shape,[0,0,0])
    assert np.allclose(m,np.eye(2)) and np.allclose(b,0)
    assert np.allclose(rigid_warp(image,[0,0,0]),image)


def test_integer_translation_sign():
    image=np.zeros((15,15));image[7,7]=1
    # Output[x] samples input[x+(2,-1)], so the feature moves to (5,8).
    warped=rigid_warp(image,[0,2,-1])
    assert np.unravel_index(warped.argmax(),warped.shape)==(5,8)


def test_inverse_generation_and_known_mapping():
    fixed=phantom();truth=np.array([12.,4.,-3.])
    m,b=affine_parameters(fixed.shape,truth);inv=np.linalg.inv(m)
    moving=affine_transform(fixed,inv,-inv@b,order=1,prefilter=False)
    aligned=rigid_warp(moving,truth)
    assert np.mean((fixed-aligned)**2)<np.mean((fixed-moving)**2)*.01
    points=np.array([[40,40],[20,40],[40,20]],float)
    assert geometric_error(fixed.shape,truth,truth,points)==0
    assert abs(geometric_error(fixed.shape,truth+[0,3,4],truth,points)-5)<1e-12


def test_4d_modality_and_fixed_mask(tmp_path):
    volume=np.zeros((80,80,2,4),np.float32)
    volume[:,:,1,0]=phantom()*100
    volume[:,:,1,1]=np.ones((80,80))*999
    path=tmp_path/'image_only.nii.gz'
    nib.save(nib.Nifti1Image(volume,np.eye(4)),path)
    fixed,moving,bounds,truth,mask,points,meta=make_anatomical_case(path,1,80,0)
    assert meta['native_shape']==[80,80,2,4]
    assert meta['modality_index']==0
    assert fixed.std()>.1 and mask.any()
    assert fixed.shape==moving.shape==mask.shape==(80,80)
    assert ((fixed[mask]-rigid_warp(moving,truth)[mask])**2).mean()<((fixed[mask]-moving[mask])**2).mean()
    assert meta['pixel_mask_count']==int(mask.sum())
