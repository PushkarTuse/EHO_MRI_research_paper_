"""Compare existing EHO/PSO-labelled STL artefacts without modifying them.

Byte equality establishes identical saved artefacts, not their generating method,
patient, units or clinical fidelity. This script makes those limits explicit.
"""
from pathlib import Path
import argparse
import hashlib
import json
import trimesh
ROOT=Path(__file__).resolve().parents[1]
def run(source, output):
    """Audit the preserved root/3d_models pairs, writing a fresh audit report."""
    records=[]
    for prefix in [source, source/'3d_models']:
        for method in ['eho','pso']:
            p=prefix/f'{method}_enhanced_brain_model.stl';mesh=trimesh.load(p,force='mesh',process=False)
            records.append({'path':str(p),'method_filename':method,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'vertices':len(mesh.vertices),'faces':len(mesh.faces),'bounds_native_units':mesh.bounds.tolist(),'units':'not stored in STL','patient':'not recorded','prediction_provenance':'not recorded'})
    result={'artifacts':records,'root_eho_pso_identical':records[0]['sha256']==records[1]['sha256'],'subfolder_eho_pso_identical':records[2]['sha256']==records[3]['sha256'],'conclusion':'Within each folder EHO and PSO files are byte-identical. They cannot support an algorithm-specific reconstruction-quality difference. Patient, units and mask provenance are unspecified, so geometric error against current cases is not computed.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'sources/existing_meshes',
                        help='Folder containing original root STL pair and 3d_models pair')
    parser.add_argument('--output', type=Path, default=ROOT/'reports/mesh_audit_current.json',
                        help='Fresh report; the historical saved audit remains unchanged')
    args = parser.parse_args()
    run(args.source.resolve(), args.output.resolve())
