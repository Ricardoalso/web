# -*- coding: utf-8 -*-
# © 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare

from odoo import api, fields, models, SUPERUSER_ID, exceptions, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_sponsored = fields.Boolean(
        compute='_compute_is_sponsored'
    )

    generated_voucher_ids = fields.One2many(
        comodel_name='sale.discount.program',
        inverse_name='source_sale_id',
        string='Generated vouchers'
    )

    discount_manually_percent = fields.Float(
        string='Manually Discount (%)',
        digits=dp.get_precision('Discount'),
        default=0.0
    )

    gift_quotation = fields.Boolean('This quotation is a gift')

    sale_order_which_use_me_in_program_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale order which use me in program',
    )
    sale_order_used_by_program_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='sale_order_which_use_me_in_program_id',
        string='Sale order used by program',
    )
    program_alert = fields.Boolean()

    @api.depends(
        'pricelist_id',
        'partner_id', 'partner_id.sponsor_id', 'partner_id.sponsor_id.active'
    )
    def _compute_is_sponsored(self):
        sponsor_pricelist = self.env.ref(
            'specific_discount_program.pricelist_sponsorship'
        )
        for sale in self:
            if not sponsor_pricelist:
                sale.is_sponsored = False
            else:
                sale.is_sponsored = sale.partner_id.sponsor_id.active \
                    and sale.pricelist_id == sponsor_pricelist

    @api.multi
    def create_partner_voucher(self, partner_id, type):
        self.ensure_one()
        months_validity = int(self.env['ir.config_parameter'].get_param(
            'voucher_default_validity', '0'
        ))

        expiration_date = None
        if months_validity:
            expiration_date = date.today() + relativedelta(
                months=months_validity
            )

        self.with_context(program_voucher=True).sudo().write({
            'generated_voucher_ids': [(0, False, {
                'partner_id': partner_id,
                'combinable': True,
                'voucher_amount': self.get_voucher_amount(),
                'max_use': 1,
                'expiration_date': expiration_date,
                'note_message_for_action':
                    _("You received a voucher."),
                'type': type
            })]
        })

    @api.multi
    def get_voucher_amount(self):
        """ Compute the amount for the voucher based on invoice amount.
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter']
        percent = float(icp.get_param('voucher_percent', '10'))
        max_amount = int(icp.get_param('voucher_max_amount', '100'))

        amount = min(
            self.amount_total * percent / 100,
            max_amount
        )
        return amount

    def search_program_to_add(self, program_to_add):
        self.ensure_one()
        return self.env['sale.discount.program'].search([
            '|',
            ('promo_code', '=', program_to_add),
            ('voucher_code', '=', program_to_add),
            '|',
            ('allowed_company_ids', 'parent_of', self.company_id.id),
            ('allowed_company_ids', '=', False),
            '|',
            ('partner_id', '=', self.partner_id.id),
            ('partner_id', '=', False),
        ], limit=1)

    @api.multi
    def action_confirm(self):

        super(SaleOrder, self).action_confirm()

        for sale in self:
            condition = (
                not sale.gift_quotation and
                sale.partner_company_type == 'agency_customer'
            )
            if condition:
                # Bon de parrainage si la commande a utilisé le programme de
                # parainnage et si le parrain est toujours valide
                if sale.is_sponsored:
                    sale.create_partner_voucher(
                        sale.partner_id.sponsor_id.partner_id.id,
                        'sponsorship_voucher'
                    )

                # Bon d'achat pour chaque commande
                sale.create_partner_voucher(sale.partner_id.id, 'voucher')

    @api.multi
    def action_cancel(self):
        result = super(SaleOrder, self).action_cancel()

        # Delete unused vouchers
        for program in self.mapped('generated_voucher_ids'):
            if program.nb_use == 0:
                program.sudo().unlink()

        # Send a email alert
        # if this order is used by another order to have promotion
        for sale in self:
            if sale.sale_order_which_use_me_in_program_id:
                sale.sale_order_which_use_me_in_program_id.program_alert = True
                template = self.env.ref(
                    'specific_discount_program.'
                    'email_template_alert_program_on_sale_order'
                )
                template.send_mail(
                    sale.sale_order_which_use_me_in_program_id.id
                )

        return result

    @api.multi
    def action_reset_alert_program(self):
        self.write({
            'program_alert': False,
        })

    @api.one
    @api.constrains('gift_quotation')
    def _check_gift_quotation_product(self):
        if self.gift_quotation:
            if not (
                len(self.order_line) == 1 and
                self.order_line[0].product_id == self.env.ref(
                    'specific_discount_program.gift_card_to_create'
                )
            ):
                raise exceptions.ValidationError(_(
                    'Only 1 (one) Gift card product is allowed to create '
                    'a gift quotation !'))

    @api.onchange('gift_quotation')
    def _onchange_gift_quotation(self):
        self._check_gift_quotation_product()

    @api.one
    @api.constrains('discount_manually_percent')
    def _check_discount_manually_percent(self):
        settings_model = self.env['sale.config.settings']
        percent = settings_model.get_default_discount_manually_percent_max(
            None
        )['discount_manually_percent_max']
        if float_compare(
                self.discount_manually_percent,
                percent,
                self.env['decimal.precision'].precision_get('Discount')
        ) == 1:
            message = _(
                'Max manually discount allowed is %s %% for a sale order.'
            ) % percent
            raise exceptions.ValidationError(message)

    @api.onchange('discount_manually_percent')
    def _onchange_discount_manually_percent(self):
        self._check_discount_manually_percent()

    @api.multi
    def apply_discount_programs(self):
        self.ensure_one()
        self.note = ''
        super(SaleOrder, self).apply_discount_programs()
        if self.discount_manually_percent:
            for line in self.order_line:
                if not line.source_program_id:
                    line.discount += self.discount_manually_percent

            model = self.env['sale.config.settings']
            message = model.get_default_discount_manually_percent_note_message(
                None
            )['discount_manually_percent_note_message']
            if message:
                if self.note and self.note != '':
                    self.note += '\n'
                self.note += message

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        res = super(SaleOrder, self)._prepare_invoice()
        res['gift_quotation'] = self.gift_quotation
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    can_edit_price_unit = fields.Boolean(
        compute='_compute_can_edit_price_unit',
        default=lambda self: self.is_siege(),
    )
    price_unit_readonly = fields.Float(
        'Unit Price',
        related='price_unit',
        readonly=True,
    )
    tax_id_readonly = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        related='tax_id',
        readonly=True,
    )

    can_edit_qty = fields.Boolean(
        compute='_compute_can_edit_qty'
    )

    @api.model
    def is_siege(self):
        return self.env.user.id == SUPERUSER_ID or self.env.user.has_group(
            'specific_security.group_siege_depiltech'
        )

    @api.depends()
    def _compute_can_edit_price_unit(self):
        """ price_unit is editable only for admin and Depiltech Admin.
        """
        admin = self.is_siege()
        for line in self:
            line.can_edit_price_unit = admin

    @api.depends('product_id', 'product_id.no_quantity')
    def _compute_can_edit_qty(self):
        """ Quantity is not editable if product has the no_quantity flag.
        """
        for line in self:
            line.can_edit_qty = not line.product_id.no_quantity

    @api.onchange('price_unit_readonly')
    def onchange_price_unit_readonly(self):
        self.price_unit = self.price_unit_readonly
