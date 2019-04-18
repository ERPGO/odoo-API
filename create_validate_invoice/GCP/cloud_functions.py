from flask import Flask, g
from flask import request
import xmlrpc.client
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import os


def env_vars( request, VAR ):
    return os.environ.get(VAR, 'Specified environment variable is not set.')


def postJsonHandlerGezWebsite( request ):
    content_type = request.headers['content-type']
    if content_type == 'application/json':
        request_json = request.get_json(silent=True)
        if request_json and 'reservation' in request_json:
            reservation = request_json['reservation']
            if not reservation:
                raise ValueError("JSON is invalid, 'reservation' property is empty")
        else:
            raise ValueError("JSON is invalid, or missing a 'reservation' property")
    else:
        raise ValueError("Unknown content type: {}".format(content_type))

    token = env_vars(request, 'TOKEN')
    # token = 'eyJhbGciOiJIUzUxMiIsImlhdCI6MTU1NTI3OTQ0NywiZXhwIjoxNTU1MjgzMDQ3fQ.eyJ1c2VybmFtZSI6ImdleiJ9.-FDjElP7HTYGPmHLUABTR86kUwicH5kxsg3luSRULYNMwu0aAhwDKYfpmZOge67lcIQPlmgjC5YSikJjt-z-0w'
    token = "Bearer " + token
    request_token = request.headers['authorization']
    if not token or token != request_token:
        raise ValueError("Auth error")

    print(request.is_json)
    content = request.get_json()
    customer = content['customer']
    product_name = content['product_name']
    product_price = content['product_price']
    invoice_line_description = content['invoice_line_description']
    reservation = content['reservation']
    reservation_type = content['reservation_type']
    GROUP = 'website'
    currency_id = 1

    url = env_vars(request, 'url')
    db = env_vars(request, 'db')
    username = env_vars(request, 'username')
    password = env_vars(request, 'password')

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
    models.execute_kw(db, uid, password, 'account.payment', 'write',
                      [[payment_id], {'invoice_ids': [(4, invoice, None)]}])
    models.execute_kw(db, uid, password, 'account.payment', 'post', [payment_id])

    invoice_search = models.execute_kw(db, uid, password, 'account.invoice', 'search_read', [[['id', '=', invoice]]])
    payment = models.execute_kw(db, uid, password, 'account.payment', 'read', [payment_id])

    return "Invoice %s created" % invoice_search[0]['number'] + "\nReservation %s created" % reservation_search[0][
        'x_name'] + "\nPayment %s created" % payment[0]['name']
