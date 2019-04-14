from variables import customer, product_name, product_price, invoice_line_description, currency_id, RESERVATION, GROUP

import xmlrpc.client

content = {
    "customer": "Kanan Mahmudov",
    "product_name": "ticket",
    "product_price": "5555",
    "invoice_line_description": "Flight ticket",
    "reservation": "5555-2332-2231-SSDD",
    "reservation_type": "Ticket"
}
customer = content['customer']
product_name = content['product_name']
product_price = content['product_price']
invoice_line_description = content['invoice_line_description']
reservation = content['reservation']
reservation_type = content['reservation_type']
GROUP = 'website'
currency_id = 1

url = "https://erpgo-gez.odoo.com"
db = "erpgo-gez-gez-demo-345789"
username = 'admin'
password = 'freebsd'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)

reservation_search = models.execute_kw(db, uid, password, 'x_reservations', 'search_read',
                                       [[['x_name', '=', reservation]]])
if not reservation_search:
    reservation_id = models.execute_kw(db, uid, password, 'x_reservations', 'create',
                                       [{'x_name': reservation, 'x_studio_type': reservation_type}])
    reservation_search = models.execute_kw(db, uid, password, 'x_reservations', 'search_read',
                                           [[['id', '=', reservation_id]]])
else:
    reservation_id = reservation_search[0]['id']

customer_search = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[['name', '=', customer]]])

if not customer_search:
    customer_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [{'name': customer}])
else:
    customer_id = customer_search[0]['id']

product = models.execute_kw(db, uid, password, 'product.template', 'search_read', [[['name', '=', product_name]]])

product_ids = []
group = models.execute_kw(db, uid, password, 'account.analytic.group', 'search_read', [[['name', '=', GROUP]]])
analytic_search = models.execute_kw(db, uid, password, 'account.analytic.account', 'search_read',
                                    [[['name', '=', reservation]]])
if not analytic_search:
    analytic_id = models.execute_kw(db, uid, password, 'account.analytic.account', 'create',
                                    [{'name': reservation, 'partner_id': customer_id, 'group_id': group[0]['id']}])
else:
    analytic_id = analytic_search[0]['id']

product_ids.append((0, 0,
                    {'product_id': product[0]['id'], 'account_analytic_id': analytic_id,
                     'name': invoice_line_description, 'price_unit': product_price,
                     'account_id': product[0]['property_account_income_id'][0]}))

invoice = models.execute_kw(db, uid, password, 'account.invoice', 'create',
                            [{'partner_id': customer_id, 'invoice_line_ids': product_ids,
                              'currency_id': currency_id}])
invoice_search = models.execute_kw(db, uid, password, 'account.invoice', 'search_read', [[['id', '=', invoice]]])

global payment_vals
payment_vals = {}
payment_method_id = models.execute_kw(db, uid, password, 'account.payment.method', 'search',
                                      [[['code', '=', 'manual'], ['payment_type', '=', 'inbound']]])
payment_vals['payment_type'] = 'inbound'
payment_vals['partner_type'] = 'customer'
payment_vals['payment_method_id'] = payment_method_id[0]
payment_vals['currency_id'] = currency_id
payment_vals['journal_id'] = 1


# models.execute_kw(db, uid, password, 'account.payment', 'write', [[payment_id], {'invoice_ids': [invoice]}])
# models.execute_kw(db, uid, password, 'account.payment', 'post', [payment_id])


def validate_invoice( invoice ):
    models.execute_kw(db, uid, password, 'account.invoice', 'action_invoice_open', [invoice])


try:
    validate_invoice(invoice)
    print("Customer Invoice {} created".format(invoice_search[0]['number']))
except:
    pass

invoice_search = models.execute_kw(db, uid, password, 'account.invoice', 'search_read', [[['id', '=', invoice]]])
payment_vals['amount'] = invoice_search[0]['amount_total']
payment_vals['payment_date'] = str(invoice_search[0]['date_invoice'])
payment_vals['partner_id'] = customer_id

payment_id = models.execute_kw(db, uid, password, 'account.payment', 'create', [payment_vals])
models.execute_kw(db, uid, password, 'account.payment', 'write', [[payment_id], {'invoice_ids': [(4, invoice, None)]}])
models.execute_kw(db, uid, password, 'account.payment', 'post', [payment_id])

invoice_search = models.execute_kw(db, uid, password, 'account.invoice', 'search_read', [[['id', '=', invoice]]])
