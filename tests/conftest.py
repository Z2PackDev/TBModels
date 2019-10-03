#!/usr/bin/env python
# -*- coding: utf-8 -*-

# (c) 2015-2018, ETH Zurich, Institut fuer Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import os
import pytest
import operator
import itertools
from functools import partial
from collections import ChainMap
try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

import numpy as np

import tbmodels
from tbmodels.io import save, load

#--------------------------FIXTURES-------------------------------------#


@pytest.fixture
def test_name(request):
    """Returns module_name.function_name for a given test"""
    return (request.module.__name__, request._parent_request._pyfuncitem.name)


@pytest.fixture
def compare_data(request, test_name, scope="session"):
    """Returns a function which either saves some data to a file or (if that file exists already) compares it to pre-existing data using a given comparison function."""

    def inner(compare_fct, data, tag=None):
        dir_name, file_name = test_name
        file_name += tag or ''
        cache_dir = str(request.config.cache.makedir(dir_name))
        file_name_full = os.path.join(cache_dir, file_name)
        try:
            val = load(file_name_full)
        except OSError:
            save(data, file_name_full)
            raise ValueError('Reference data does not exist.')
        else:
            assert compare_fct(val, data)

    return inner


@pytest.fixture
def compare_equal(compare_data):
    return lambda data, tag=None: compare_data(operator.eq, data, tag)


@pytest.fixture
def compare_isclose(compare_data):
    return lambda data, tag=None: compare_data(np.allclose, data, tag)


@pytest.fixture
def models_equal():
    def inner(model1, model2, ignore_sparsity=False):
        assert model1.size == model2.size
        assert model1.dim == model2.dim
        assert np.array(model1.uc == model2.uc).all()
        assert model1.occ == model2.occ
        for k in model1.hop.keys() | model2.hop.keys():
            print('k:', k)
            print('model1:\n', np.array(model1.hop[k]))
            print('model2:\n', np.array(model2.hop[k]))
            assert (np.array(model1.hop[k]) == np.array(model2.hop[k])).all()
        assert (model1.pos == model2.pos).all()
        if not ignore_sparsity:
            assert model1._sparse == model2._sparse
        return True

    return inner


@pytest.fixture
def kdotp_models_equal():
    def inner(model1, model2):
        for pow in model1.taylor_coefficients.keys() | model1.taylor_coefficients.keys():
            assert (np.array(model1.taylor_coefficients[pow]) == np.array(model2.taylor_coefficients[pow])).all()
        return True

    return inner


@pytest.fixture
def models_close():
    def inner(model1, model2, ignore_sparsity=False):
        assert model1.size == model2.size
        assert model1.dim == model2.dim
        if model1.uc is None:
            assert model1.uc == model2.uc
        else:
            assert np.isclose(model1.uc, model2.uc).all()
        assert model1.occ == model2.occ
        for k in model1.hop.keys() | model2.hop.keys():
            print('k:', k)
            print('model1:\n', np.array(model1.hop[k]))
            print('model2:\n', np.array(model2.hop[k]))
            assert np.isclose(np.array(model1.hop[k]), np.array(model2.hop[k])).all()
        if model1.pos is None:
            assert model1.pos == model2.pos
        else:
            assert np.isclose(model1.pos, model2.pos).all()
        if not ignore_sparsity:
            assert model1._sparse == model2._sparse
        return True

    return inner


@pytest.fixture
def sample():
    def inner(name):
        return os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples'), name)

    return inner


#-----------------------------------------------------------------------#
@pytest.fixture
def get_model_clean():
    def inner(t1, t2, sparsity_default=False, **kwargs):
        dim = kwargs.get('dim', 3)
        defaults = {}
        defaults['pos'] = [[0] * 2, [0.5] * 2]
        if dim < 2:
            raise ValueError('dimension must be at least 2')
        elif dim > 2:
            for p in defaults['pos']:
                p.extend([0] * (dim - 2))
        defaults['occ'] = 1
        defaults['on_site'] = (1, -1)
        defaults['size'] = 2
        defaults['dim'] = None
        defaults['sparse'] = sparsity_default
        model = tbmodels.Model(**ChainMap(kwargs, defaults))

        for phase, R in zip([1, -1j, 1j, -1], itertools.product([0, -1], [0, -1], [0])):
            model.add_hop(t1 * phase, 0, 1, R)

        for R in ((r[0], r[1], 0) for r in itertools.permutations([0, 1])):
            model.add_hop(t2, 0, 0, R)
            model.add_hop(-t2, 1, 1, R)
        return model

    return inner


@pytest.fixture(params=[True, False])
def sparse(request):
    return request.param


@pytest.fixture()  # params is for sparse / dense
def get_model(get_model_clean, sparse):
    return partial(get_model_clean, sparsity_default=sparse)
