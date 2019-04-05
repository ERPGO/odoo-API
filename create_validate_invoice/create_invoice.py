from variables import customer, product_name, product_price, invoice_line_description, currency_id, RESERVATION, GROUP

url = "https://erpgo-gez-prod-345771.dev.odoo.com"
db = "erpgo-gez-prod-345771"
username = 'admin'
password = 'freebsd'

import xmlrpc.client

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)


customer_search = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[['name', '=', customer]]])

if not customer_search:
    customer_id = models.execute_kw(db, uid, password, 'res.partner', 'create', [{'name': customer}])
else:
    customer_id = customer_search[0]['id']

product = models.execute_kw(db, uid, password, 'product.template', 'search_read', [[['name', '=', product_name]]])

product_ids = []
group = models.execute_kw(db, uid, password, 'account.analytic.group', 'search_read', [[['name', '=', GROUP]]])
analytic_search = models.execute_kw(db, uid, password, 'account.analytic.account', 'search_read', [[['name', '=', RESERVATION]]])
if not analytic_search:
    analytic_id = models.execute_kw(db, uid, password, 'account.analytic.account', 'create',
                                    [{'name': RESERVATION, 'partner_id': customer_id, 'group_id': group[0]['id']}])
else:
    analytic_id = analytic_search[0]['id']

product_ids.append((0, 0,
                    {'product_id': product[0]['id'], 'account_analytic_id': analytic_id, 'name': invoice_line_description, 'price_unit': product_price,
                     'account_id': product[0]['property_account_income_id'][0]}))

invoice = models.execute_kw(db, uid, password, 'account.invoice', 'create',
                            [{'partner_id': customer_id, 'invoice_line_ids': product_ids, 'currency_id': currency_id}])

def validate_invoice( invoice ):
    models.execute_kw(db, uid, password, 'account.invoice', 'action_invoice_open', [invoice])

try:
    validate_invoice(invoice)
except:
    pass

