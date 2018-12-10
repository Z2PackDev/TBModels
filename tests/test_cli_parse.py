#!/usr/bin/env python
# -*- coding: utf-8 -*-

# © 2015-2018, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import pytest
import tempfile
from click.testing import CliRunner

import tbmodels
from tbmodels._cli import cli


@pytest.mark.parametrize('pos_kind', ['wannier', 'nearest_atom'])
@pytest.mark.parametrize('prefix', ['silicon', 'bi'])
def test_cli_parse(models_equal, prefix, sample, pos_kind):
    runner = CliRunner()
    with tempfile.NamedTemporaryFile() as out_file:
        run = runner.invoke(
            cli, ['parse', '-o', out_file.name, '-f',
                  sample(''), '-p', prefix, '--pos-kind', pos_kind],
            catch_exceptions=False
        )
        print(run.output)
        model_res = tbmodels.Model.from_hdf5_file(out_file.name)
    model_reference = tbmodels.Model.from_wannier_folder(folder=sample(''), prefix=prefix, pos_kind=pos_kind)
    models_equal(model_res, model_reference)
