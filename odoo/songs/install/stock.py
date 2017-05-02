# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from pkg_resources import resource_stream

import anthem

from anthem.lyrics.loaders import load_csv_stream
from ..common import req


@anthem.log
def load_warehouses(ctx):
    """ Importing warehouses from CSV """
    content = resource_stream(req, 'data/install/stock.warehouse.csv')
    load_csv_stream(ctx, 'stock.warehouse', content, delimiter=',')


@anthem.log
def main(ctx):
    """ Configuring stock """
    load_warehouses(ctx)
