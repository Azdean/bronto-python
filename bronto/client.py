from suds import WebFault
from suds.client import Client as SudsClient

API_ENDPOINT = 'https://api.bronto.com/v4?wsdl'


class BrontoError(Exception):
    pass


class Client(object):
    _valid_contact_fields = ['email', 'mobileNumber', 'status', 'msgPref',
                             'source', 'customSource', 'listIds', 'fields',
                             'SMSKeywordIDs']
    _valid_order_fields = ['id', 'email', 'contactId', 'products', 'orderDate',
                           'tid']
    _valid_product_fields = ['id', 'sku', 'name', 'description', 'category',
                             'image', 'url', 'quantity', 'price']

    def __init__(self, token, **kwargs):
        if not token or not isinstance(token, basestring):
            raise ValueError('Must supply a token as a non empty string.')

        self._token = token
        self._client = None

    def login(self):
        self._client = SudsClient(API_ENDPOINT)
        try:
            self.session_id = self._client.service.login(self._token)
            session_header = self._client.factory.create('sessionHeader')
            session_header.sessionId = self.session_id
            self._client.set_options(soapheaders=session_header)
        except WebFault as e:
            raise BrontoError(e.message)

    def add_contacts(self, contacts):
        final_contacts = []
        for contact in contacts:
            if not isinstance(contact, dict):
                raise ValueError('Each contact must be a dictionary of contact attributes')
            if not any([contact.get('email'), contact.get('mobileNumber')]):
                raise ValueError('Must provide either an email or mobileNumber')
            contact_obj = self._client.factory.create('contactObject')
            # FIXME: Add special handling for listIds, fields and SMSKeywordIDs
            for field, value in contact:
                if field not in self._valid_contact_fields:
                    raise KeyError('Invalid contact attribute: %s' % field)
                setattr(contact_obj, field, value)
            final_contacts.append(contact_obj)
        try:
            response = self._client.service.addContacts(final_contacts)
            if response.errors:
                err_str = ', '.join(['%s: %s' % (response.results[x].errorCode,
                                                 response.results[x].errorString)
                                     for x in response.errors])
                raise BrontoError('An error occurred while adding contacts: %s'
                                  % err_str)
        except WebFault as e:
            raise BrontoError(e.message)
        return response

    def add_contact(self, contact):
        return self.add_contacts([contact, ])

    def get_contacts(self, emails):
        final_emails = []
        filter_operator = self._client.factory.create('filterOperator')
        fop = filter_operator.EqualTo
        for email in emails:
            contact_email = self._client.factory.create('stringValue')
            contact_email.operator = fop
            contact_email.value = email
            final_emails.append(contact_email)
        contact_filter = self._client.factory.create('contactFilter')
        contact_filter.email = final_emails
        if len(final_emails) > 1:
            filter_type = self._client.factory.create('filterType')
            contact_filter.type = filter_type.OR

        try:
            response = self._client.service.readContacts(contact_filter,
                                                        pageNumber=1)
        except WebFault as e:
            raise BrontoError(e.message)
        return response

    def get_contact(self, email):
        return self.get_contacts([email, ])

    def add_orders(self, orders):
        final_orders = []
        for order in orders:
            if not order.get('id', None):
                raise ValueError('Each order must provide an id')
            order_obj = self._client.factory.create('orderObject')
            for field, value in order:
                if field == 'products':
                    final_products = []
                    for product in value:
                        product_obj = self._client.factory.create('productObject')
                        for pfield, pvalue in product:
                            if pfield not in self._valid_product_fields:
                                raise KeyError('Invalid product attribute: %s'
                                               % pfield)
                            setattr(product_obj, pfield, pvalue)
                        final_products.append(product_obj)
                    order_obj.products = final_products
                elif field not in self._valid_order_fields:
                    raise KeyError('Invalid order attribute: %s' % field)
                else:
                    setattr(order_obj, field, value)
            final_orders.append(order_obj)
        try:
            response = self._client.service.addOrUpdateOrders(orders)
            if response.errors:
                err_str = ', '.join(['%s: %s' % (response.results[x].errorCode,
                                                 response.results[x].errorString)
                                     for x in response.errors])
                raise BrontoError('An error occurred while adding orders: %s'
                                  % err_str)
        except WebFault as e:
            raise BrontoError(e.message)
        return response

    def add_order(self, order):
        return self.add_orders([order, ])
