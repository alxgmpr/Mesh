# coding=utf-8
import threading
from logger import Logger
from product import Product
from variant import Variant
from time import time, sleep
import json
import requests

logt = Logger().logt
log = Logger().log

# api keys used for headers
JD_API_KEY = '1A17CC86AC974C8D9047262E77A825A4'
SZ_API_KEY = 'EA0E72B099914EB3BA6BE90A21EA43A9'
FP_API_KEY = '5F9D749B65CD44479C1BA2AA21991925'
# user agents for headers
FP_UA = 'FootPatrol/2.0 CFNetwork/808.3 Darwin/16.3.0'
JD_UA = 'JDSports/5.3.1.207 CFNetwork/808.3 Darwin/16.3.0'
SZ_UA = 'Size-APPLEPAY/4.0 CFNetwork/808.3 Darwin/16.3.0'
# scraping categories
FP_CAT = 'footwear/all-footwear'
SZ_CAT = 'mens/footwear'
JD_CAT = 'men/mens-footwear'


class Mesh(threading.Thread):
    def __init__(self, config_filename, tid):
        threading.Thread.__init__(self)
        logt(tid, 'MeshAPI by Luke Davis (@R8T3D)')
        logt(tid, 'ATC by Alex Gompper (@573supreme/@edzart)')
        logt(tid, 'Improved by ServingShoes (@ServingShoescom)\n')
        try:  # import the config file settings. see config.json for help
            with open(config_filename) as config:
                self.c = json.load(config)
        except IOError:
            raise('couldnt open config file {}'.format(config_filename))
        else:
            logt(tid, '[init] loaded config file: {}'.format(config_filename))
        self.S = requests.session()
        self.tid = tid
        self.start_time = time()
        self.proxy = self.c['proxy']
        self.matches = []  # Matching product list. Proceed if we only find one (or pick)
        self.sizes = self.c['product']['sizes']
        self.keywords = self.c['product']['positive_kw'].split(
    ',')  # Positive keywords (must match all keywords)
        self.negatives = self.c['product']['negative_kw'].split(
            ',')  # Negative keywords (matching any of these discards item)
        self.headers = {
            'Host': 'commerce.mesh.mx',
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Debug': '1',
            'Accept-Language': 'en-gb',
            'MESH-Commerce-Channel': 'iphone-app'
        }
        # distinguish between sites, load respective API keys
        if self.c['site'].lower() == 'sz':
            logt(tid, '[init] running on size')
            self.headers['X-API-Key'] = SZ_API_KEY
            self.headers['User-Agent'] = SZ_UA
            self.sitename = 'size'
        elif self.c['site'].lower() == 'fp':
            logt(tid, '[init] running on fp')
            self.headers['X-API-Key'] = FP_API_KEY
            self.headers['User-Agent'] = FP_UA
            self.sitename = 'footpatrol'
        elif self.c['site'].lower() == 'jd':
            logt(tid, '[init] running on jd')
            self.headers['X-API-Key'] = JD_API_KEY
            self.headers['User-Agent'] = JD_UA
            self.sitename = 'jdsports'
        else:
            raise Exception('unrecognized site code in config')

    def get_all_products(self, count):
        # scrape products from category pages.
        # returns a list of product objects
        logt(self.tid, 'scraping product categories')
        products = []
        params = {
            "from": 0,
            "max": count,
            "channel": "iphone-app"
        }
        if self.c['site'].lower() == 'jd':
            url = 'https://commerce.mesh.mx/stores/jdsports/products/category/{}'.format(JD_CAT)
        elif self.c['site'].lower() == 'fp':
            url = 'https://commerce.mesh.mx/stores/footpatrol/products/category/{}'.format(FP_CAT)
        else:
            url = 'https://commerce.mesh.mx/stores/size/products/category/{}'.format(SZ_CAT)
        r = requests.get(
            url,
            params=params,
            headers=self.headers
        )
        r.raise_for_status()
        try:
            r = r.json()
            for prod in r['products']:
                name = prod['name'].encode('utf-8').strip()
                try:
                    name = '{} {}'.format(name, prod['colour'])
                except KeyError:
                    name = prod['name']
                p = Product(
                    prod['SKU'].encode('utf-8').strip(),
                    name,
                    prod['stockStatus'].encode('utf-8').strip()
                )
                products.append(p)
            logt(self.tid, 'found {} products'.format(len(r['products'])))
            return products
        except KeyError:
            raise Exception('couldnt parse category json')

    def select_product(self, product_list):
        # compare a product against keywords set in the config json
        # appends product matches to global self.matches list
        logt(self.tid, 'selecting matching product from list len: {}'.format(len(product_list)))
        for p in product_list:
            match = True
            for neg in self.negatives:
                if neg in p.name:
                    match = False
            for key in self.keywords:
                if key not in p.name:
                    match = False
            if match:
                self.matches.append(p)
                logt(self.tid,"[match] found a match {} \t {}".format(p.sku, p.name))

        logt(self.tid,"[matches] found {} matching item(s)".format(len(self.matches)))
        #raise Exception('select_product() isnt implemented yet')

    def get_product_skus(self, product):
        # scrape product variants and stock status from its info
        # returns a list of variant objects
        logt(self.tid, 'fetching product variants')
        variants=[]
        try:
            params = {
                "expand": "variations,informationBlocks,customisations",
                "channel": "iphone-app"
            }
            url = "https://commerce.mesh.mx/stores/{}/products/{}".format(self.sitename, product)
            r = requests.request(
                'GET',
                url,
                headers=self.headers,
                params=params
            ).json()

            for size in r['options']:
                logt(self.tid,"[size] {}  \t sku {} \t {}".format(
                    size,
                    r['options'][size]['SKU'],
                    r['options'][size]['stockStatus']
                ))
                v = Variant(
                    size,
                    r['options'][size]['SKU'],
                    r['options'][size]['stockStatus']
                )
                variants.append(v)
            return variants
        except KeyError:
            logt(self.tid,"[error] exception while getting product info json")
            exit(-1)
        #raise Exception('get_product_skus() isnt implemented yet')

    def select_sku(self, variant_list):
        # compares product variants against sizes in config json
        # returns True if found a matching sku for the list of our sizes and adds that sku to global variable skupid
        logt(self.tid, 'selecting matching variant from list')
        self.skupid = None
        for var in self.sizes:
                for var2 in variant_list:
                    if var==var2.size:
                        logt(self.tid,"[match] found a matching size {} with sku {}".format(var2.size, var2.sku))
                        self.skupid = var2.sku
                        return True
        logt(self.tid, "[error] didnt find a matching size {}".format(self.sizes))
        return False
        #raise Exception('select_sku() isnt implemented yet')

    def add_to_cart(self, variant):
        # adds a particular variant to cart
        # returns the cart ID as a string
        logt(self.tid, 'adding variant to cart')
        if self.c['site'].lower == 'jd':
            url = "https://commerce.mesh.mx/stores/jdsports/carts"
            payload = {
                "channel": "iphone-app",
                "contents": [{
                    "$schema": "https://commerce.mesh.mx/stores/jdsports/schema/CartProduct",
                    "SKU": self.c['product']['preset_sku'],
                    "quantity": 1
                }]
            }
        else:
            url = "https://commerce.mesh.mx/stores/{}/carts".format(self.sitename)
            payload = {
                "channel": "iphone-app",
                "products": [{
                    "SKU": variant.sku,
                    "quantity": 1
                }]
            }
        r = self.S.post(
            url,
            headers=self.headers,
            json=payload
        )

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            print r.text
            r.raise_for_status()

        try:
            return r.json()['ID']
        except KeyError:
            #return False
            raise Exception('couldnt find new cart id')

    def get_customer_ids(self):
        # creates a new customer
        # returns customer and address IDs as strings
        logt(self.tid, 'creating new customer/address ids')
        url = "https://commerce.mesh.mx/stores/{}/customers".format(self.sitename)
        data = {
            "phone": self.c['checkout']['phone'],
            "gender": "",
            "firstName": self.c['checkout']['fname'],
            "addresses": [{
                "locale": self.c['checkout']['locale'],
                "county": self.c['checkout']['state'],
                "country": self.c['checkout']['country'],
                "address1": self.c['checkout']['addr1'],
                "town": self.c['checkout']['city'],
                "postcode": self.c['checkout']['zip'],
                "isPrimaryBillingAddress": True,
                "isPrimaryAddress": True,
                "address2": self.c['checkout']['addr2']
            }],
            "title": "",
            "email": self.c['checkout']['email'],
            "isGuest": True,
            "lastName": self.c['checkout']['lname']
        }
        r = self.S.post(
            url,
            headers=self.headers,
            json=data
        )
        r.raise_for_status()
        try:
            return r.json()['ID'], r.json()['addresses'][0]['ID']
        except KeyError:
            raise Exception('couldnt parse customer creation json')

    def submit_customer(self, customer_id, address_id, cart_id):
        # submits customer and address ids as strings
        logt(self.tid, 'submitting customer/address ids')
        url = "https://commerce.mesh.mx/stores/{}/carts/{}".format(self.sitename, cart_id)
        if self.c['site'].lower() is 'jd':
            data = {
                "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/carts\\/{}".format(cart_id),
                "customer": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}".format(customer_id)
                },
                "billingAddress": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}\/addresses\\/{}".format(
                        customer_id,
                        address_id
                    )
                },
                "deliveryAddress": {
                    "id": "https:\\/\\/commerce.mesh.mx\\/stores\\/jdsports\\/customers\\/{}\\/addresses\\/{}".format(
                        customer_id,
                        address_id
                    )
                }
            }
        else:
            data = {
                "customerID": customer_id,
                "billingAddressID": address_id,
                "deliveryAddressID": address_id
            }
        r = self.S.put(
            url,
            headers=self.headers,
            json=data
        )
        r.raise_for_status()

    def get_hosted_payment(self, cart_id):
        # starts the datacash hosted payment
        # returns hps session ID and payment callback url as strings
        logt(self.tid, 'starting hosted payment')
        url = "https://commerce.mesh.mx/stores/{}/carts/{}/hostedPayment".format(self.sitename, cart_id)
        data = {
            "type": "CARD",
            "terminals": {
                "successURL": "https://ok",
                "failureURL": "https://fail",
                "timeoutURL": "https://timeout"
            }
        }
        r = self.S.post(
            url,
            headers=self.headers,
            json=data
        )
        r.raise_for_status()
        try:
            return r.json()['terminalEndPoints']['hostedPageURL'].split('HPS_SessionID=')[1], \
                   r.json()['href'].split('payments/')[1]
        except KeyError:
            raise Exception('couldnt parse hosted payment json')

    def submit_payment(self, hps_id):
        # submits the cc information to the datacash session
        # returns payment token as string
        logt(self.tid, 'opening payment page')
        url = "https://hps.datacash.com/hps/?HPS_SessionID={}".format(hps_id)
        headers = {
            "Host": "hps.datacash.com",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_2 like Mac OS X) AppleWebKit/603.2.4 (KHTML, like Gecko) Mobile/14F89",
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip,deflate"
        }
        r = self.S.get(
            url,
            headers=headers
        )
        r.raise_for_status()
        logt(self.tid, 'submitting payment')
        url = "https://hps.datacash.com/hps/"
        data = {
            "card_number": self.c['checkout']['cc'],
            "exp_month": self.c['checkout']['exp_m'],
            "exp_year": self.c['checkout']['exp_y'],
            "cv2_number": self.c['checkout']['cvv'],
            "issue_number": "",
            "HPS_SessionID": hps_id,
            "action": "confirm",
            "continue": ""
        }
        headers = {
            "Host": "hps.datacash.com",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://hps.datacash.com",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_2 like Mac OS X) AppleWebKit/603.2.4 (KHTML, like Gecko) Mobile/14F89",
            "Referer": "https://hps.datacash.com/hps/?HPS_SessionID={}".format(hps_id),
            "Accept-Language": "en-us",
            "Accept-Encoding": "gzip,deflate"
        }
        r = self.S.post(
            url,
            headers=headers,
            data=data,
            allow_redirects=False
        )
        return r.headers['Location']

    def fire_callback(self, callback_id, payment_token):
        # submits the callback with payment token
        # returns the completed order number as a string
        logt(self.tid, 'firing payment callback')
        url = 'https://commerce.mesh.mx/stores/{}/payments/{}/hostedpaymentresult'.format(self.sitename, callback_id)
        data = {
            "HostedPaymentPageResult": payment_token
        }
        r = self.S.post(
            url,
            headers=self.headers,
            data=data
        )
        r.raise_for_status()
        try:
            if r.json()['status'] == 'DECLINED':
                #print r.text
                raise Exception('card was declined')
            return r.json()['orderClientID']
        except KeyError:
            raise Exception('unable to parse callback response json')

    def run(self):
        if self.c['product']['preset_sku'] is None:
            logt(self.tid, 'MODE 1: SCRAPING TO FIND MATCHING PRODUCT')
            while len(self.matches) < 1:
                products=self.get_all_products(600)
                self.select_product(products)
                if len(self.matches) < 1:
                    logt(self.tid,"[sleep] no matches, waiting and refreshing")
                    self.products = []  # Clear product list
                    sleep(self.c['poll_time'])
            while(True):
                variants=self.get_product_skus(self.matches[0].sku)
                if self.select_sku(variants):
                    loop = True
                    while loop:
                        try:
                            cart_id = self.add_to_cart(Variant(0, self.skupid, True))
                            loop = False
                        except requests.exceptions.HTTPError:
                            logt(self.tid, 'couldnt atc, sleeping and retrying')
                            sleep(self.c['poll_time'])
                    logt(self.tid, 'got cart id {}'.format(cart_id))
                    customer_id, address_id = self.get_customer_ids()
                    logt(self.tid, 'got cust id {}'.format(customer_id))
                    logt(self.tid, 'got addr id {}'.format(address_id))
                    self.submit_customer(customer_id, address_id, cart_id)
                    loop = True
                    while loop:
                        try:
                            hps_id, payment_callback = self.get_hosted_payment(cart_id)
                            loop = False
                        except requests.exceptions.HTTPError:
                            logt(self.tid, 'couldnt raise invoice, sleeping and retrying')
                            sleep(self.c['poll_time'])
                    logt(self.tid, 'got hps id {}'.format(hps_id))
                    logt(self.tid, 'got callback {}'.format(payment_callback))
                    token = self.submit_payment(hps_id)
                    order = self.fire_callback(payment_callback, token)
                    logt(self.tid, 'order id {}'.format(order))
                    logt(self.tid, '[time] time to complete: {} sec'.format(abs(self.start_time-time())))
                    break #outterloop
                sleep(self.c['poll_time'])
        else:
            if len(self.c['product']['preset_sku']) == 6:
                logt(self.tid, 'MODE 2 - RESTOCK: USING PREDEFINED SKU: {}'.format(self.c['product']['preset_sku']))
                while(True):
                    variants=self.get_product_skus(self.c['product']['preset_sku'])
                    if self.select_sku(variants):
                        loop = True
                        while loop:
                            try:
                                cart_id = self.add_to_cart(Variant(0, self.skupid, True))
                                loop = False
                            except requests.exceptions.HTTPError:
                                logt(self.tid, 'couldnt atc, sleeping and retrying')
                                sleep(self.c['poll_time'])
                        logt(self.tid, 'got cart id {}'.format(cart_id))
                        customer_id, address_id = self.get_customer_ids()
                        logt(self.tid, 'got cust id {}'.format(customer_id))
                        logt(self.tid, 'got addr id {}'.format(address_id))
                        self.submit_customer(customer_id, address_id, cart_id)
                        loop = True
                        while loop:
                            try:
                                hps_id, payment_callback = self.get_hosted_payment(cart_id)
                                loop = False
                            except requests.exceptions.HTTPError:
                                logt(self.tid, 'couldnt raise invoice, sleeping and retrying')
                                sleep(self.c['poll_time'])
                        logt(self.tid, 'got hps id {}'.format(hps_id))
                        logt(self.tid, 'got callback {}'.format(payment_callback))
                        token = self.submit_payment(hps_id)
                        order = self.fire_callback(payment_callback, token)
                        logt(self.tid, 'order id {}'.format(order))
                        logt(self.tid, '[time] time to complete: {} sec'.format(abs(self.start_time-time())))
                        break #outterloop
                    sleep(self.c['poll_time'])
            elif len(self.c['product']['preset_sku']) == 13:
                logt(self.tid, 'MODE 3: USING PREDEFINED SKU.PID: {}'.format(self.c['product']['preset_sku']))
                loop = True
                while loop:
                    try:
                        cart_id = self.add_to_cart(Variant(0, self.c['product']['preset_sku'], True))
                        loop = False
                    except requests.exceptions.HTTPError:
                        logt(self.tid, 'couldnt atc, sleeping and retrying')
                        sleep(self.c['poll_time'])
                logt(self.tid, 'got cart id {}'.format(cart_id))
                customer_id, address_id = self.get_customer_ids()
                logt(self.tid, 'got cust id {}'.format(customer_id))
                logt(self.tid, 'got addr id {}'.format(address_id))
                self.submit_customer(customer_id, address_id, cart_id)
                loop = True
                while loop:
                    try:
                        hps_id, payment_callback = self.get_hosted_payment(cart_id)
                        loop = False
                    except requests.exceptions.HTTPError:
                        logt(self.tid, 'couldnt raise invoice, sleeping and retrying')
                        sleep(self.c['poll_time'])
                logt(self.tid, 'got hps id {}'.format(hps_id))
                logt(self.tid, 'got callback {}'.format(payment_callback))
                token = self.submit_payment(hps_id)
                order = self.fire_callback(payment_callback, token)
                logt(self.tid, 'order id {}'.format(order))
                logt(self.tid, '[time] time to complete: {} sec'.format(abs(self.start_time-time())))
            else:
                raise Exception('malformed preset sku')
