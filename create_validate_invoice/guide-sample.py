# encoding: utf-8
import odoorpc
from datetime import datetime


HOST = 'localhost'
PORT = 8069
DB = 'DB_NAME'
USER = 'USER_MAIL'
PASS = 'PASSWORD_USER'

PARTNER = {}
TAX_ID = None
payment_vals = {}


def create_invoice(odoo, invoice_args):
    """
    Create the invoice header, with partner_id, date start, date due
    refer to account.invoice table
    :param odoo: odoo client
    :param invoice_args: 'partner_id, name, comment
    :return: invoice id
    """
    invoice_model = odoo.env['account.invoice']
    new_invoice_id = invoice_model.create(invoice_args)
    return new_invoice_id


def create_invoice_line(odoo, invoice_line_args, TAX_ID):
    """
    Create details line for invoice see account.invoice.line table
    :param odoo: odoo client
    :param invoice_line_args: invoice_id name product_id account_id price_unit price_subtotal quantity, and much if you want
    :param TAX_ID: tax id from account.tax, dependend of your account plan
    :return:
    """
    invoice_line_model = odoo.env['account.invoice.line']
    invoice_line_id = invoice_line_model.create(invoice_line_args)
    invoice_line_model.browse(invoice_line_id).invoice_line_tax_ids = TAX_ID
    invoice_model = odoo.env['account.invoice']
    invoice_model.browse(invoice_line_args['invoice_id']).compute_taxes()


def open_invoice(odoo, invoice_id):
    """
    Validate invoice to open, at this point the invoice can't be removed
    :param odoo: odoo client
    :param invoice_id: id invoice
    :return:
    """
    odoo.execute('account.invoice', 'action_invoice_open', invoice_id)


def create_payment(odoo, vals, invoice_id):
    """
    Create payment line
    :param odoo: odoo client
    :param vals: amount, pay_date
    :param invoice_id: id of invoice
    :return:
    """
    mod = odoo.env['account.payment']
    id = mod.create(vals)
    mod.browse(id).invoice_ids = [invoice_id]
    mod.browse(id).post()


def initial_value(odoo, company_id):
    """
    initialise generic information for the script, obviously you can send information in your data
    :param odoo: odoo client
    :param company_id: your company id
    :return:
    """
    global payment_vals
    global TAX_ID
    account_payment_method_model = odoo.env['account.payment.method']
    payment_method_id = \
    account_payment_method_model.search([('code', '=', 'manual'), ('payment_type', '=', 'inbound')])[0]
    res_currency_model = odoo.env['res.currency']
    res_currency_id = res_currency_model.search([('name', '=', 'EUR')])[0]
    account_account_model = odoo.env['account.account']
    account_account_id = account_account_model.search([('company_id', '=', company_id), ('name', '=', 'Banque')])[0]
    account_journal_model = odoo.env['account.journal']
    journal_id = account_journal_model.search([('default_debit_account_id', '=', account_account_id)])[0]
    payment_vals['payment_type'] = 'inbound'
    payment_vals['partner_type'] = 'customer'
    payment_vals['payment_method_id'] = payment_method_id
    payment_vals['currency_id'] = res_currency_id
    payment_vals['journal_id'] = journal_id
    partner_model = odoo.env['account.tax']
    TAX_ID = partner_model.search([('name', '=', "TVA 21%")])


def insert_complete_invoice(host, port, user, password, database, company_id, invoice_values):
    """

    :param company_id: id of own company
    :param invoice_values: all data values in dictionnary like this :
    {
     'partner_id': id_of_parner
     'name': reference of invoice
     'comment': comment of invoice
     'invoice_lines': [
        {
            'invoice_id': invoice_id, #complete when invoice is created
            'name' : 'name field',
            'product_id': product_id,
            'account_id': account_id,
            'price_unit': price_unit,
            'price_subtotal': price_subtotal,
            'quantity': quantity,
         }, {...}
     ]
     'invoice_payment_lines': [
        {
           'amount'
           'pay_date'
         }, {...}

     ]
    }
    :return:
    """
    try:
        odoo = odoorpc.ODOO(host, port=port)
        odoo.login(database, user, password)
        initial_value(odoo, company_id)

        invoice_id = create_invoice(odoo, invoice_values)
        for invoice_value in invoice_values['invoice_lines']:
            invoice_value['invoice_id'] = invoice_id
            create_invoice_line(odoo, invoice_value, TAX_ID)
        open_invoice(odoo, invoice_id)
        for invoice_payment_line in invoice_values['invoice_payment_lines']:
            payment_vals['amount'] = invoice_payment_line['amount']
            payment_vals['payment_date'] = invoice_payment_line['payment_date']
            payment_vals['partner_id'] = invoice_values['partner_id']
            create_payment(odoo, payment_vals, invoice_id)

        odoo.logout()
    except:
        return False

    return True



if __name__ == '__main__':
    # TODO faire une méthode qui  reprend les product id
    complete_invoice = {
        'partner_id': PARTNER_ID,
        'name': 'name',
        'comment': 'content',
        'invoice_lines': [
            {
                'invoice_id': None,
                'name' : 'name field',
                'product_id': PRODUCT_ID,
                'account_id': ACCOUNT_ID,
                'price_unit': PRICE_UNIT,
                'price_subtotal': PRICE_SUBTOTAL,
                'quantity': QUANTITY,
            }
        ],
        'invoice_payment_lines': [
            {
                'amount': AMOUNT,
                'payment_date': str(datetime.now())
            },
        ]

    }
    insert_complete_invoice(HOST,PORT,USER,PASS,DB,COMAPNY_ID, complete_invoice)