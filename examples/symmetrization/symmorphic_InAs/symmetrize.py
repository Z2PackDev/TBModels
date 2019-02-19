#!/usr/bin/env python
# -*- coding: utf-8 -*-

# (c) 2015-2018, ETH Zurich, Institut fuer Theoretische Physik
# Authors: Georg Winkler, Dominik Gresch <greschd@gmx.ch>

import os

import numpy as np
import scipy.linalg as la
import matplotlib.pyplot as plt
import tbmodels as tb
import pymatgen as mg
import pymatgen.symmetry.analyzer
import pymatgen.symmetry.bandstructure
from symmetry_representation import SymmetryOperation


def spin_reps(prep):
    """
    Calculates the spin rotation matrices. The formulas to determine the rotation axes and angles
    are taken from `here <http://scipp.ucsc.edu/~haber/ph116A/rotation_11.pdf>`_.

    :param prep:   List that contains 3d rotation matrices.
    :type prep:    list(array)
    """
    # general representation of the D1/2 rotation about the axis (l,m,n) around the
    # angle phi
    D12 = lambda l, m, n, phi: np.array([[np.cos(phi / 2.) - 1j * n * np.sin(phi / 2.), (-1j * l - m) * np.sin(phi / 2.)],
                                         [(-1j * l + m) * np.sin(phi / 2.), np.cos(phi / 2.) + 1j * n * np.sin(phi / 2.)]])

    n = np.zeros(3)
    tr = np.trace(prep)
    det = np.round(np.linalg.det(prep), 5)
    if det == 1.:  # rotations
        theta = np.arccos(0.5 * (tr - 1.))
        if theta != 0:
            n[0] = prep[2, 1] - prep[1, 2]
            n[1] = prep[0, 2] - prep[2, 0]
            n[2] = prep[1, 0] - prep[0, 1]
            if np.round(np.linalg.norm(n), 5) == 0.:  # theta = pi, that is C2 rotations
                e, v = la.eig(prep)
                n = v[:, list(np.round(e, 10)).index(1.)]
                spin = np.round(D12(n[0], n[1], n[2], np.pi), 15)
            else:
                n /= np.linalg.norm(n)
                spin = np.round(D12(n[0], n[1], n[2], theta), 15)
        else:  # case of unity
            spin = D12(0, 0, 0, 0)
    elif det == -1.:  # improper rotations and reflections
        theta = np.arccos(0.5 * (tr + 1.))
        if np.round(theta, 5) != np.round(np.pi, 5):
            n[0] = prep[2, 1] - prep[1, 2]
            n[1] = prep[0, 2] - prep[2, 0]
            n[2] = prep[1, 0] - prep[0, 1]
            if np.round(np.linalg.norm(n), 5) == 0.:  # theta = 0 (reflection)
                e, v = la.eig(prep)
                # normal vector is eigenvector to eigenvalue -1
                n = v[:, list(np.round(e, 10)).index(-1.)]
                # spin is a pseudovector!
                spin = np.round(D12(n[0], n[1], n[2], np.pi), 15)
            else:
                n /= np.linalg.norm(n)
                # rotation followed by reflection:
                spin = np.round(np.dot(D12(n[0], n[1], n[2], np.pi), D12(n[0], n[1], n[2], theta)), 15)
        else:  # case of inversion (does not do anything to spin)
            spin = D12(0, 0, 0, 0)
    return np.array(spin)


def compare_bands_plot(model1, model2, structure):
    path = mg.symmetry.bandstructure.HighSymmKpath(structure)
    kpts, labels = path.get_kpoints(line_density=200)
    # de-duplicate / merge labels
    for i in range(len(labels) - 1):
        if labels[i] and labels[i + 1]:
            if labels[i] != labels[i + 1]:
                labels[i] = labels[i] + ' | ' + labels[i + 1]
            labels[i + 1] = ''

    # E-fermi is just an approximation
    efermi = model1.eigenval([0, 0, 0])[model1.occ]
    E1 = [model1.eigenval(k) for k in kpts]
    E2 = [model2.eigenval(k) for k in kpts]

    plt.figure()
    labels_clean = []
    labels_idx = []
    for i, l in enumerate(labels):
        if l:
            labels_idx.append(i)
            labels_clean.append('$' + l + '$')
    for i in labels_idx[1:-1]:
        plt.axvline(i, color='b')
    plt.plot(range(len(kpts)), E1 - efermi, 'k')
    plt.plot(range(len(kpts)), E2 - efermi, 'r', lw=0.5)
    plt.xticks(labels_idx, labels_clean)
    plt.xlim([0, len(kpts) - 1])
    plt.ylim([-6, 6])
    plt.savefig('results/compare_bands.pdf', bbox_inches='tight')


if __name__ == '__main__':
    model_nosym = tb.Model.from_hdf5_file('data/model_nosym.hdf5')
    reference_model = tb.Model.from_hdf5_file('data/reference_model.hdf5')

    # change the order of the orbitals from (In: s, py, pz, px; As: py, pz, px) * 2
    # to (In: s, px, py, pz; As: s, px, py, pz) * 2
    model_nosym = model_nosym.slice_orbitals([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])

    # set up symmetry operations
    time_reversal = SymmetryOperation(
        rotation_matrix=np.eye(3), repr_matrix=np.kron([[0, -1j], [1j, 0]], np.eye(7)), repr_has_cc=True
    )

    structure = mg.Structure(
        lattice=model_nosym.uc, species=['In', 'As'], coords=np.array([[0, 0, 0], [0.25, 0.25, 0.25]])
    )

    # get real-space representations
    analyzer = mg.symmetry.analyzer.SpacegroupAnalyzer(structure)
    symops = analyzer.get_symmetry_operations(cartesian=False)
    symops_cart = analyzer.get_symmetry_operations(cartesian=True)
    rots = [x.rotation_matrix for x in symops]
    taus = [x.translation_vector for x in symops]

    # get corresponding represesentations in the Hamiltonian basis
    reps = []
    for n, (rot, tau) in enumerate(zip(rots, taus)):
        C = symops_cart[n].rotation_matrix
        tauc = symops_cart[n].translation_vector
        prep = C
        spinrep = spin_reps(C)
        R = np.kron(spinrep, la.block_diag(1., prep, prep))
        reps.append(R)

    # set up the space group symmetries
    symmetries = [
        SymmetryOperation(
            # r-space and k-space matrices are related by transposing and inverting
            rotation_matrix=rot,
            repr_matrix=repr_mat,
            repr_has_cc=False
        ) for rot, repr_mat in zip(rots, reps)
    ]

    os.makedirs('results', exist_ok=True)
    model_tr = model_nosym.symmetrize([time_reversal])
    model = model_tr.symmetrize(symmetries, full_group=True)
    model.to_hdf5_file('results/model.hdf5')

    compare_bands_plot(model_nosym, model, structure)
    for R in set(model.hop.keys()) | set(reference_model.hop.keys()):
        assert np.isclose(model.hop[R], reference_model.hop[R]).all()

    # Check that the symmetries are fulfilled at some random k
    k = (0.12312351, 0.73475412, 0.2451235)
    assert np.isclose(
        model.hamilton(k, convention=1),
        time_reversal.repr.matrix @
        # when complex conjugation is present, r-space matrix (R) and k-space matrix (K)
        # are related by K = -(R.T)^{-1}
        # -> K^{-1} = -R.T
        model.hamilton(-time_reversal.rotation_matrix.T @ k, convention=1).conjugate() @
        time_reversal.repr.matrix.conjugate().T
    ).all()

    for sym in symmetries:
        assert np.isclose(
            model.hamilton(k, convention=1),
            sym.repr.matrix @
            # k-space and r-space matrices are related by transposing and inverting
            # -> k-matrix^{-1} == r-matrix.T
            model.hamilton(sym.rotation_matrix.T @ k, convention=1) @
            sym.repr.matrix.conjugate().T
        ).all()
