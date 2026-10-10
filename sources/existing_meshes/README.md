# Preserved historical surface files

The two STL files in this directory came from the original dataset folder; the
two in the 3d_models subfolder came from its original 3d_models subfolder.
Their filenames and binary contents are preserved. Within each pair the EHO
and PSO files are byte-identical. Patient identity, units and generating method
were not recorded.

The historical audit is saved at results/existing_meshes/mesh_audit.json.
Run python src/audit_existing_meshes.py from the repository root to audit the
preserved files in the current clone; this writes a separate current audit in
reports/mesh_audit_current.json.
