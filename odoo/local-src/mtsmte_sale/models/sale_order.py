# -*- coding: utf-8 -*-
# Author: Denis Leemann
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    analyze_sample = fields.Text(
        string='Samples To Analyze',
    )

    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.project_id:
                continue
            prj = self.env['project.project'].search(
                [('analytic_account_id', '=', order.project_id.id)])
            vals = {
                # We don't know if related or not
                'analyze_sample': order.analyze_sample
            }
            prj.write(vals)
            for line in order.order_line:
                task = self.env['project.task'].search(
                    [('sale_line_id', '=', line.id)])
                # Adding measures todo in tasks
                product_substance_measure = []
                for substance in line.product_substance_ids:
                    vals_measure = {
                        'task_id': task.id,
                        'product_substance_id': substance.id,
                    }
                    product_substance_measure += [(0, 0, vals_measure)]
                task.write({
                    'product_substance_measure_ids': product_substance_measure,
                })
        return True
