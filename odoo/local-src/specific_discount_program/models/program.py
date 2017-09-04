# -*- coding: utf-8 -*-
# © 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Program(models.Model):
    _inherit = 'sale.discount.program'

    allowed_company_ids = fields.Many2many(
        comodel_name='res.company',
        string='Allowed company',
    )

    partner_company_id = fields.Many2one(
        comodel_name='res.company',
        related='partner_id.company_id',
        store=True
    )

    # For vouchers created by sale.order
    source_sale_id = fields.Many2one(comodel_name='sale.order',
                                     string='Source sale')
    # For vouchers created by account.invoice
    source_invoice_id = fields.Many2one(comodel_name='account.invoice',
                                        string='Source invoice')

    customer_required = fields.Boolean('Requires customer',
                                       compute='_compute_cust_req')

    type = fields.Selection(selection_add=[
        ('gift_voucher', 'Gift voucher'),
        ('sponsorship_voucher', 'Sponsorship voucher')])

    note_message_for_action = fields.Char(
        string='Voucher description',
    )

    _sql_constraints = [
        ('voucher_source_sale_id',
         'check(source_sale_id is null or voucher_code is not null)',
         _("source_sale_id can be filled only for voucher")),
        ('voucher_source_invoice_id',
         'check(source_invoice_id is null or voucher_code is not null)',
         _('source_invoice_id can be filled only for voucher'))
    ]

    @api.depends(
        'program_name', 'voucher_code', 'promo_code', 'voucher_amount',
        'partner_id', 'type'
    )
    def _compute_name(self):
        for program in self:
            if program.type == 'gift_voucher':
                program.name = _("Gift: %s (%s)") % (
                    program.voucher_code,
                    program.voucher_amount
                )
            elif program.voucher_code:
                program.name = "%s: %s (%s)" % (
                    program.partner_id.name,
                    program.voucher_code,
                    program.voucher_amount
                )

            else:
                super(Program, program)._compute_name()

    @api.multi
    def _compute_cust_req(self):
        for prog in self:
            prog.customer_required = self.env.context.get('program_voucher',
                                                          False)

    @api.model
    def create(self, vals):
        """ Set promo code not combinable
        """
        if vals.get('promo_code'):
            vals['combinable'] = False
        return super(Program, self).create(vals)

    @api.multi
    def check_voucher_limits(self, sale):
        super(Program, self).check_voucher_limits(sale)

        max_vouchers = int(self.env['ir.config_parameter'].get_param(
            'voucher_max_count', '0'
        ))
        if max_vouchers:
            nb_vouchers = len(sale.program_code_ids.filtered(
                lambda p: p.voucher_amount
            ))

            if nb_vouchers > max_vouchers:
                raise UserError(
                    _("Number of vouchers is limited to %s")
                    % max_vouchers
                )

    @api.model
    def get_automatic_programs(self, order):
        domain = [
            '&',
            ('automatic', '=', True),
            '|',
            ('allowed_company_ids', '=', False),
            ('allowed_company_ids', 'parent_of', order.company_id.id)
        ]

        return self.search(domain)

    @api.model
    def reset_sale_programs(self, sale):
        """ Always remove discount because discount is readonly for Depiltech
        """
        sale.ensure_one()
        for line in sale.order_line:
            if not line.source_program_id:
                line.write({
                    'discount': False
                })
        sale.sale_order_used_by_program_ids.write({
            'sale_order_which_use_me_in_program_id': False,
        })
        super(Program, self).reset_sale_programs(sale)

    def _get_action_values_for_voucher_amount(self, product_add_price):
        values = super(Program, self)._get_action_values_for_voucher_amount(
            product_add_price
        )
        if self.type == 'gift_voucher':
            values['product_add_id'] = self.env.ref(
                'specific_discount_program.gift_card_to_use'
            ).id
        if self.note_message_for_action:
            values['note_message'] = self.note_message_for_action
        return values

    @api.multi
    def apply_actions(self, sale):
        self.ensure_one()
        for condition in self.condition_ids:
            another_order_validated_used = (
                condition.type_condition == 'another_order_validated' and
                condition.check(sale)
            )
            if another_order_validated_used:
                condition.get_another_order_validated(
                    sale
                ).sale_order_which_use_me_in_program_id = sale.id
        return super(Program, self).apply_actions(sale)
